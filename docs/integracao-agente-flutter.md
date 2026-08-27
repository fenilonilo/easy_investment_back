# Consultor de Ativos — Guia de integração Flutter

Agente de chat especializado em gestão e avaliação de ativos financeiros. Seis endpoints sob `/ai`: conversa em JSON, conversa em streaming e gestão das conversas do usuário.

| | |
|---|---|
| **Base URL** | `http://localhost:8000` |
| **Auth** | Bearer JWT (validade de 1h) |
| **Formatos** | JSON · SSE (`text/event-stream`) |
| **Docs vivas** | `http://localhost:8000/docs` (Swagger UI) |

---

## Índice

- [Visão geral](#visão-geral)
- [Autenticação](#autenticação)
- [Modelo mental](#modelo-mental)
- [Fluxo de integração](#fluxo-de-integração)
- **Endpoints**
  - [`POST /ai/chat`](#post-aichat--conversa-em-json)
  - [`POST /ai/chat/stream`](#post-aichatstream--conversa-em-streaming)
  - [`GET /ai/sessions`](#get-aisessions--listar-conversas)
  - [`GET /ai/sessions/{id}`](#get-aisessionsid--histórico-de-uma-conversa)
  - [`GET /ai/sessions/{id}/summary`](#get-aisessionsidsummary--resumo-de-uma-conversa)
  - [`DELETE /ai/sessions/{id}`](#delete-aisessionsid--apagar-uma-conversa)
- [Protocolo SSE](#protocolo-sse)
- **Implementação Dart**
  - [Models](#models-dart)
  - [Cliente HTTP](#cliente-http)
  - [Cliente de streaming](#cliente-de-streaming)
  - [Uso na tela](#uso-na-tela)
- [Tabela de erros](#tabela-de-erros)
- [Armadilhas](#armadilhas)

---

## Visão geral

O agente conversa sobre mercado financeiro e usa ferramentas de verdade para responder: consulta cotação, histórico, dividendos, notícias e indicadores fundamentalistas ao vivo, e busca explicações de métricas numa base de conhecimento própria. Ele nunca inventa número de mercado.

Do lado do app, isso importa por três motivos práticos:

- **A resposta vem em Markdown.** O agente usa tabelas, listas, negrito e blocos de código. Renderize com `flutter_markdown` — texto puro vai mostrar os asteriscos.
- **A resposta demora.** Uma pergunta que dispara duas ou três ferramentas leva de 5 a 30 segundos. Streaming não é enfeite; sem ele a tela fica parada.
- **O contexto do usuário é automático.** Watchlist e perfil de investidor são injetados no servidor a cada mensagem. O app *não* precisa mandar isso.

### Convenções deste documento

| Marca | Significado |
|---|---|
| **obrigatório** | Campo sem o qual a requisição falha com 422 |
| *opcional* | Pode ser omitido; nunca envie `null` explícito onde o campo é opcional |
| `{session_id}` | Parâmetro de caminho, substituído pelo valor real |

---

## Autenticação

Todos os endpoints `/ai` exigem um JWT no header `Authorization`. O token sai do login.

> ### ⚠️ Atenção — o login NÃO é JSON
>
> `POST /auth/login` usa `application/x-www-form-urlencoded`, não JSON, porque implementa o padrão OAuth2 do FastAPI. E o campo do e-mail chama `username`, não `email`.
>
> Mandar JSON devolve **422** e é o erro número um de quem integra pela primeira vez.

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=felipe%40email.com&password=minhasenha
```

**200 OK:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Daí em diante, todo request para `/ai` leva:

```http
Authorization: Bearer <access_token>
```

> ### ⚠️ Expiração — não existe refresh token
>
> O token vale **1 hora** e a API **não tem endpoint de refresh**. Quando ele expira, as chamadas passam a devolver **401** e o app precisa refazer o login.
>
> Guarde as credenciais em `flutter_secure_storage` e trate 401 num interceptor: tente relogar uma vez e repita a requisição; se falhar de novo, mande o usuário para a tela de login.

---

## Modelo mental

### Sessões são as conversas

Uma **sessão** é uma thread de conversa, identificada por um `session_id` (UUID em string). O servidor guarda o histórico: o app **não** reenvia mensagens anteriores, manda só a nova.

- Enviar `/ai/chat` **sem** `session_id` começa uma conversa nova. O id criado volta no campo `session_id` da resposta — guarde-o.
- Enviar **com** `session_id` continua aquela conversa, com todo o contexto anterior.
- As últimas 5 interações entram inteiras no contexto; o que é mais antigo entra resumido, automaticamente.

> **Isolamento entre usuários:** um `session_id` que pertence a outra pessoa devolve sempre **404**, nunca 403 — inclusive no `/ai/chat`. Não existe como ler a conversa de terceiro chutando id.

### Watchlist e perfil entram sozinhos

A cada mensagem o servidor lê a watchlist e o `investor_profile` (`CONSERVATIVE`, `MODERATE` ou `AGGRESSIVE`) do usuário autenticado e injeta no contexto do modelo. O usuário pode perguntar *"como está minha carteira?"* sem o app enviar nada além do texto. Alterações feitas em `/profile/watchlist` valem já na mensagem seguinte.

### O agente pode escrever na watchlist

Se o usuário pedir *"adiciona PETR4 na minha lista"*, o agente executa a alteração e confirma no texto. O escopo é rígido: só a watchlist do próprio usuário autenticado.

**Consequência para o app:** depois de uma resposta cujo `tools_used` contenha `adicionar_a_watchlist` ou `remover_da_watchlist`, invalide o cache local da watchlist — ela mudou no servidor.

### Dois modelos, troca transparente

O modelo principal é o Gemini; se ele estourar cota ou cair, a requisição é repetida automaticamente na Groq. O campo `provider` (`"gemini"` ou `"groq"`) diz quem respondeu. Isso é informativo — não exige nenhum tratamento no app, e o usuário não precisa ver.

---

## Fluxo de integração

Ordem em que as telas normalmente consomem a API.

1. **Login.** `POST /auth/login` (form-urlencoded) → guarda o `access_token`.
2. **Lista de conversas.** `GET /ai/sessions` → tela de histórico, ordenada da mais recente para a mais antiga.
3. **Abrir uma conversa.** `GET /ai/sessions/{id}` → carrega as mensagens anteriores na tela de chat.
4. **Enviar mensagem.** `POST /ai/chat/stream` → tokens aparecem em tempo real. Sem `session_id` na primeira mensagem.
5. **Guardar o id.** O evento `start` já traz o `session_id` — persista antes de a resposta terminar, para não perder a conversa se o app fechar no meio.
6. **Apagar.** `DELETE /ai/sessions/{id}` → 204, sem corpo.

---

## `POST /ai/chat` — conversa em JSON

Resposta completa de uma vez.

### Corpo da requisição

| Campo | Tipo | | Descrição |
|---|---|---|---|
| `message` | `string` | **obrigatório** | Texto do usuário. Entre **1 e 4000** caracteres — fora disso, 422. |
| `session_id` | `string` | *opcional* | Conversa a continuar. Omita para criar uma nova. |

```json
{
  "message": "o P/L da PETR4 está caro comparado com a minha watchlist?",
  "session_id": "0f9c2a7e-4b31-4f8d-9a11-6c2e5b8d3f40"
}
```

### Resposta · 200 OK

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | `string` | Id da conversa. **Sempre presente**, inclusive quando foi criada agora. |
| `run_id` | `string?` | Id desta execução. Útil só para suporte e log; pode vir `null`. |
| `content` | `string` | Resposta do agente, **em Markdown**. |
| `provider` | `string` | `"gemini"` ou `"groq"`. |
| `model_used` | `string` | Id do modelo, ex.: `"gemini-3.5-flash"`. |
| `tools_used` | `string[]` | Ferramentas acionadas. Lista vazia se o agente respondeu só com conhecimento próprio. |

```json
{
  "session_id": "0f9c2a7e-4b31-4f8d-9a11-6c2e5b8d3f40",
  "run_id": "b71d0c94-5e2a-4c6b-8f13-2a9e7d4c1b85",
  "content": "**PETR4** está a R$ 38,42 com P/L de 4,8x...\n\n| Ativo | P/L |\n|---|---|\n| PETR4 | 4,8x |\n| VALE3 | 6,1x |",
  "provider": "gemini",
  "model_used": "gemini-3.5-flash",
  "tools_used": ["cotacao_atual", "resumo_financeiro"]
}
```

### Códigos de erro

| Código | Quando |
|---|---|
| `401` | Token ausente, inválido ou expirado |
| `404` | `session_id` pertence a outro usuário |
| `422` | `message` vazia ou acima de 4000 caracteres |
| `502` | Nenhum provider de IA conseguiu responder |

```bash
curl -X POST http://localhost:8000/ai/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "o que é ROE?"}'
```

> **Timeout:** esta rota pode levar **30 segundos ou mais** quando o agente encadeia ferramentas. O timeout padrão do `http` do Dart não cobre isso — configure pelo menos 90 s, ou prefira a rota de streaming, que dá feedback imediato ao usuário.

---

## `POST /ai/chat/stream` — conversa em streaming

Corpo **idêntico** ao `/ai/chat`. O que muda é a resposta: `Content-Type: text/event-stream`, entregue em pedaços conforme o modelo gera.

### Headers da resposta

```http
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

### Códigos de erro

| Código | Quando |
|---|---|
| `401` | Token ausente, inválido ou expirado |
| `404` | `session_id` pertence a outro usuário — verificado **antes** de abrir o stream |
| `422` | `message` fora de 1–4000 caracteres |

> ### ⚠️ Não existe 502 aqui
>
> Uma vez que o status **200** foi enviado, não dá mais para virar erro HTTP. Falha do modelo depois disso chega como um **evento `error` dentro do stream**, com o HTTP em 200.
>
> Tratar só o status code deixa esse caso passar silenciosamente — o app precisa tratar o evento.

---

## `GET /ai/sessions` — listar conversas

Mais recentes primeiro.

### Query params

| Param | Tipo | Padrão | Descrição |
|---|---|---|---|
| `limit` | `int` | `50` | Máximo de conversas retornadas |

### Resposta · 200 OK — array de objetos

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | `string` | Id da conversa |
| `created_at` | `int?` | **Unix timestamp em segundos** |
| `updated_at` | `int?` | **Unix timestamp em segundos** — use este para ordenar na tela |
| `runs_count` | `int` | Quantas trocas de mensagem a conversa tem |
| `summary` | `string?` | Resumo gerado. **Vem `null` em conversas curtas** — o resumo só é produzido depois de algumas trocas. Use como subtítulo do item da lista, com fallback. |
| `topics` | `string[]` | Tópicos extraídos do resumo. Pode vir vazio pelo mesmo motivo. |

```json
[
  {
    "session_id": "0f9c2a7e-4b31-4f8d-9a11-6c2e5b8d3f40",
    "created_at": 1755100800,
    "updated_at": 1755104412,
    "runs_count": 7,
    "summary": "Comparação de P/L entre PETR4 e VALE3, e como ler o indicador",
    "topics": ["P/L", "valuation", "PETR4"]
  },
  {
    "session_id": "3ab19f55-8c02-4e7d-b6a3-91f4c7e28d16",
    "created_at": 1754996100,
    "updated_at": 1754996240,
    "runs_count": 1,
    "summary": null,
    "topics": []
  }
]
```

---

## `GET /ai/sessions/{id}` — histórico de uma conversa

### Resposta · 200 OK

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | `string` | Id da conversa |
| `messages` | `object[]` | Mensagens em ordem cronológica |
| `messages[].role` | `string?` | `"user"`, `"assistant"`, `"system"` ou `"tool"` |
| `messages[].content` | `string?` | Texto da mensagem, em Markdown quando `role` é `assistant` |
| `messages[].created_at` | `int?` | Unix timestamp em segundos |

> ### ⚠️ Filtre os papéis antes de renderizar
>
> O histórico inclui mensagens internas de `system` e de `tool` — instruções do agente e retornos brutos das ferramentas em JSON. Mostrar isso na tela vaza o prompt e polui a conversa.
>
> Renderize apenas `role == "user"` e `role == "assistant"`, e descarte itens com `content` nulo ou vazio.

```json
{
  "session_id": "0f9c2a7e-4b31-4f8d-9a11-6c2e5b8d3f40",
  "messages": [
    { "role": "user",      "content": "o que é ROE?",                  "created_at": 1755100800 },
    { "role": "assistant", "content": "**ROE** (Return on Equity)...", "created_at": 1755100807 }
  ]
}
```

### Códigos de erro

| Código | Quando |
|---|---|
| `401` | Token ausente, inválido ou expirado |
| `404` | Conversa não existe ou é de outro usuário |

---

## `GET /ai/sessions/{id}/summary` — resumo de uma conversa

O mesmo resumo que aparece em `GET /ai/sessions`, isolado. Útil para um cabeçalho de conversa ou uma tela de detalhes.

| Campo | Tipo | Descrição |
|---|---|---|
| `session_id` | `string` | Id da conversa |
| `summary` | `string?` | `null` se ainda não houve trocas suficientes |
| `topics` | `string[]` | Tópicos extraídos |
| `updated_at` | `string?` | **String ISO 8601** — veja o aviso abaixo |

> ### 🚨 Inconsistência real de tipo — não é engano do documento
>
> `updated_at` **aqui é uma string ISO 8601** (`"2026-08-13T14:20:12.184000"`), enquanto `created_at` e `updated_at` em `/ai/sessions` são **inteiros unix em segundos**. São dois formatos diferentes na mesma API.
>
> Use `DateTime.parse()` neste campo e `DateTime.fromMillisecondsSinceEpoch(v * 1000)` nos outros. Reaproveitar o mesmo parser nos dois quebra em runtime.

```json
{
  "session_id": "0f9c2a7e-4b31-4f8d-9a11-6c2e5b8d3f40",
  "summary": "Comparação de P/L entre PETR4 e VALE3, e como ler o indicador",
  "topics": ["P/L", "valuation", "PETR4"],
  "updated_at": "2026-08-13T14:20:12.184000"
}
```

### Códigos de erro

| Código | Quando |
|---|---|
| `401` | Token ausente, inválido ou expirado |
| `404` | Conversa não existe ou é de outro usuário |

---

## `DELETE /ai/sessions/{id}` — apagar uma conversa

Sucesso responde **204 No Content**, **com corpo vazio**. Não tente fazer `jsonDecode` da resposta — vai lançar exceção.

| Código | Significado |
|---|---|
| `204` | Apagada. Sem corpo. |
| `401` | Token ausente, inválido ou expirado |
| `404` | Conversa não existe ou é de outro usuário |

```bash
curl -X DELETE http://localhost:8000/ai/sessions/0f9c2a7e-4b31-4f8d-9a11-6c2e5b8d3f40 \
  -H "Authorization: Bearer $TOKEN" -i
```

---

## Protocolo SSE

> ### 🚨 `EventSource` não serve aqui
>
> O padrão `EventSource` (e os pacotes Dart construídos em cima dele) só faz **GET** e não permite header `Authorization` customizado. Esta rota é **POST com corpo JSON e Bearer token**.
>
> A solução é usar `http.Request` + `client.send()` e consumir `response.stream` na mão — está pronto mais abaixo.

### Formato do frame

Cada evento é um bloco de linhas terminado por **uma linha em branco**. Sempre duas linhas: o nome do evento e o payload JSON.

```
event: start
data: {"session_id": "0f9c2a7e-...", "provider": "gemini", "model": "gemini-3.5-flash"}

event: tool
data: {"name": "cotacao_atual"}

event: token
data: {"content": "**PETR4** está "}

event: token
data: {"content": "a R$ 38,42 hoje."}

event: done
data: {"session_id": "0f9c2a7e-...", "provider": "gemini", "model": "gemini-3.5-flash", "content": "**PETR4** está a R$ 38,42 hoje."}
```

### Os cinco eventos

| Evento | Payload | Descrição |
|---|---|---|
| `start` | `{ session_id, provider, model }` | Sempre o primeiro. Traz o **session_id** — persista aqui, não espere o `done`. |
| `token` | `{ content }` | Pedaço do texto. Concatene na ordem de chegada. Chega zero ou muitas vezes. |
| `tool` | `{ name }` | O agente começou a executar uma ferramenta. Bom gancho para um indicador do tipo *"consultando cotação…"*. **`name` pode vir `null`** — tenha um texto genérico de fallback. |
| `done` | `{ session_id, provider, model, content }` | Terminador normal. O campo `content` traz a resposta **inteira** — use-o como fonte da verdade final, em vez da sua concatenação de tokens. |
| `error` | `{ detail, session_id?, request_id? }` | Falha. Leia o aviso abaixo: nem sempre encerra o stream. |

> ### Sempre mostre o `request_id` na tela de erro
>
> Toda resposta da API traz o header **`X-Request-ID`**, e todo frame `error` traz o campo **`request_id`**. Esse mesmo id aparece em cada linha de log do servidor daquela requisição.
>
> Exibir o id no aviso de erro (algo como *"Erro ao responder · cód. a1b2c3d4e5f6"*) transforma "a IA deu erro" em uma busca de um comando no log do backend. Sem ele, não há como ligar o relato ao traceback.
>
> O corpo dos erros **502** também inclui o id no final do `detail`.

> ### ⚠️ O evento `error` tem dois comportamentos diferentes
>
> **Erro fatal** (o modelo nem começou, ou a conexão caiu): chega um `error` e o stream **fecha sem** `done`.
>
> **Erro parcial** (o modelo abortou a geração no meio): chega um `error`, o stream **continua** e ainda termina com `done`, possivelmente com conteúdo parcial.
>
> **Regra prática:** trate `done` como o único terminador legítimo. Se o stream fechar sem ele, o último `error` era fatal — mostre a mensagem e ofereça reenviar.

---

## Models Dart

Sem dependência de code-gen — `fromJson` escrito à mão para colar direto. Único pacote necessário: `http`.

```dart
// lib/agente/models.dart
import 'dart:convert';

/// Resposta de POST /ai/chat.
class ChatResponse {
  final String sessionId;
  final String? runId;
  final String content; // Markdown
  final String provider; // "gemini" | "groq"
  final String modelUsed;
  final List<String> toolsUsed;

  const ChatResponse({
    required this.sessionId,
    required this.runId,
    required this.content,
    required this.provider,
    required this.modelUsed,
    required this.toolsUsed,
  });

  factory ChatResponse.fromJson(Map<String, dynamic> json) => ChatResponse(
        sessionId: json['session_id'] as String,
        runId: json['run_id'] as String?,
        content: json['content'] as String? ?? '',
        provider: json['provider'] as String? ?? '',
        modelUsed: json['model_used'] as String? ?? '',
        toolsUsed:
            (json['tools_used'] as List?)?.cast<String>() ?? const <String>[],
      );

  /// A watchlist mudou no servidor? Então invalide o cache local.
  bool get alterouWatchlist => toolsUsed.any(
        (t) => t == 'adicionar_a_watchlist' || t == 'remover_da_watchlist',
      );
}

/// Item de GET /ai/sessions.
class SessionInfo {
  final String sessionId;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final int runsCount;
  final String? summary;
  final List<String> topics;

  const SessionInfo({
    required this.sessionId,
    required this.createdAt,
    required this.updatedAt,
    required this.runsCount,
    required this.summary,
    required this.topics,
  });

  /// Aqui os timestamps são INTEIROS unix em segundos.
  static DateTime? _fromUnix(dynamic v) => v is int
      ? DateTime.fromMillisecondsSinceEpoch(v * 1000, isUtc: true).toLocal()
      : null;

  factory SessionInfo.fromJson(Map<String, dynamic> json) => SessionInfo(
        sessionId: json['session_id'] as String,
        createdAt: _fromUnix(json['created_at']),
        updatedAt: _fromUnix(json['updated_at']),
        runsCount: json['runs_count'] as int? ?? 0,
        summary: json['summary'] as String?,
        topics: (json['topics'] as List?)?.cast<String>() ?? const <String>[],
      );

  /// Título para a lista de conversas, já com fallback para resumo ausente.
  String get titulo =>
      (summary != null && summary!.trim().isNotEmpty) ? summary! : 'Nova conversa';
}

/// Item de GET /ai/sessions/{id}.
class ChatMessage {
  final String role; // user | assistant | system | tool
  final String content;
  final DateTime? createdAt;

  const ChatMessage({
    required this.role,
    required this.content,
    required this.createdAt,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) => ChatMessage(
        role: json['role'] as String? ?? '',
        content: json['content'] as String? ?? '',
        createdAt: SessionInfo._fromUnix(json['created_at']),
      );

  bool get ehDoUsuario => role == 'user';

  /// system e tool são internos do agente — nunca vão para a tela.
  bool get exibivel =>
      (role == 'user' || role == 'assistant') && content.trim().isNotEmpty;
}

/// Resposta de GET /ai/sessions/{id}/summary.
class SessionSummary {
  final String sessionId;
  final String? summary;
  final List<String> topics;
  final DateTime? updatedAt;

  const SessionSummary({
    required this.sessionId,
    required this.summary,
    required this.topics,
    required this.updatedAt,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) => SessionSummary(
        sessionId: json['session_id'] as String,
        summary: json['summary'] as String?,
        topics: (json['topics'] as List?)?.cast<String>() ?? const <String>[],
        // ATENÇÃO: aqui é ISO 8601 (string), não unix. Diferente de SessionInfo.
        updatedAt: json['updated_at'] is String
            ? DateTime.tryParse(json['updated_at'] as String)
            : null,
      );
}

/// Erro vindo da API, já com a mensagem pronta para exibir.
class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException(this.statusCode, this.message);

  factory ApiException.fromResponse(int status, String body) {
    String detalhe;
    try {
      final decoded = jsonDecode(body);
      final d = decoded is Map<String, dynamic> ? decoded['detail'] : null;
      if (d is String) {
        detalhe = d;
      } else if (d is List && d.isNotEmpty) {
        // 422 do FastAPI: detail é uma LISTA de erros de validação.
        final primeiro = d.first;
        detalhe = primeiro is Map ? '${primeiro['msg']}' : d.toString();
      } else {
        detalhe = body;
      }
    } catch (_) {
      detalhe = body.isEmpty ? 'Erro $status' : body;
    }
    return ApiException(status, detalhe);
  }

  /// Mensagem para o usuário final.
  String get mensagemAmigavel => switch (statusCode) {
        401 => 'Sua sessão expirou. Entre novamente.',
        404 => 'Conversa não encontrada.',
        422 => 'Mensagem inválida: $message',
        502 => 'O assistente está indisponível. Tente em alguns instantes.',
        _ => message,
      };

  @override
  String toString() => 'ApiException($statusCode): $message';
}
```

> ### ⚠️ O campo `detail` muda de tipo conforme o erro
>
> Em 401, 404 e 502 o FastAPI devolve `{"detail": "texto"}`. Em **422** devolve `{"detail": [{...}, {...}]}` — uma **lista**. Assumir string sempre quebra na validação. O `ApiException.fromResponse` acima já cobre os dois.

---

## Cliente HTTP

```dart
// lib/agente/agente_api.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

import 'models.dart';

class AgenteApi {
  AgenteApi({required this.baseUrl, required this.getToken, http.Client? client})
      : _client = client ?? http.Client();

  /// Emulador Android: use 'http://10.0.2.2:8000' — 'localhost' aponta
  /// para o próprio emulador, não para a máquina que roda a API.
  final String baseUrl;

  /// Callback para o token atual, para não segurar um valor expirado.
  final String Function() getToken;

  final http.Client _client;

  void dispose() => _client.close();

  Map<String, String> get _headers => {
        'Authorization': 'Bearer ${getToken()}',
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
      };

  /// Sempre use utf8.decode(bodyBytes) — response.body assume latin-1
  /// quando o servidor não declara o charset, e acentos viram lixo.
  dynamic _decode(http.Response r) {
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw ApiException.fromResponse(r.statusCode, utf8.decode(r.bodyBytes));
    }
    if (r.bodyBytes.isEmpty) return null;
    return jsonDecode(utf8.decode(r.bodyBytes));
  }

  // ---------------------------------------------------------------- chat

  Future<ChatResponse> enviarMensagem({
    required String message,
    String? sessionId,
  }) async {
    final r = await _client
        .post(
          Uri.parse('$baseUrl/ai/chat'),
          headers: _headers,
          body: jsonEncode({
            'message': message,
            if (sessionId != null) 'session_id': sessionId,
          }),
        )
        // O agente encadeia ferramentas: 30s+ é normal.
        .timeout(const Duration(seconds: 120));

    return ChatResponse.fromJson(_decode(r) as Map<String, dynamic>);
  }

  // ------------------------------------------------------------ sessões

  Future<List<SessionInfo>> listarConversas({int limit = 50}) async {
    final r = await _client.get(
      Uri.parse('$baseUrl/ai/sessions?limit=$limit'),
      headers: _headers,
    );
    final lista = _decode(r) as List;
    return lista
        .map((e) => SessionInfo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Devolve só o que vai para a tela — system e tool ficam de fora.
  Future<List<ChatMessage>> carregarHistorico(String sessionId) async {
    final r = await _client.get(
      Uri.parse('$baseUrl/ai/sessions/$sessionId'),
      headers: _headers,
    );
    final json = _decode(r) as Map<String, dynamic>;
    return (json['messages'] as List)
        .map((e) => ChatMessage.fromJson(e as Map<String, dynamic>))
        .where((m) => m.exibivel)
        .toList();
  }

  Future<SessionSummary> obterResumo(String sessionId) async {
    final r = await _client.get(
      Uri.parse('$baseUrl/ai/sessions/$sessionId/summary'),
      headers: _headers,
    );
    return SessionSummary.fromJson(_decode(r) as Map<String, dynamic>);
  }

  Future<void> apagarConversa(String sessionId) async {
    final r = await _client.delete(
      Uri.parse('$baseUrl/ai/sessions/$sessionId'),
      headers: _headers,
    );
    // 204 sem corpo: não decodifique.
    if (r.statusCode != 204) {
      throw ApiException.fromResponse(r.statusCode, utf8.decode(r.bodyBytes));
    }
  }
}
```

---

## Cliente de streaming

Um `sealed class` para os eventos e um parser de SSE que lida com os frames na mão.

```dart
// lib/agente/agente_stream.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

import 'models.dart';

// ------------------------------------------------------------- eventos

sealed class AgentEvent {
  const AgentEvent();

  static AgentEvent? parse(String evento, String dados) {
    final Map<String, dynamic> j;
    try {
      j = jsonDecode(dados) as Map<String, dynamic>;
    } catch (_) {
      return null; // frame malformado: ignore em vez de derrubar o chat
    }
    return switch (evento) {
      'start' => StartEvent(
          sessionId: j['session_id'] as String? ?? '',
          provider: j['provider'] as String? ?? '',
          model: j['model'] as String? ?? '',
        ),
      'token' => TokenEvent(j['content'] as String? ?? ''),
      'tool' => ToolEvent(j['name'] as String?),
      'done' => DoneEvent(
          sessionId: j['session_id'] as String? ?? '',
          provider: j['provider'] as String? ?? '',
          model: j['model'] as String? ?? '',
          content: j['content'] as String? ?? '',
        ),
      'error' => ErrorEvent(
          detail: j['detail'] as String? ?? 'Erro desconhecido',
          sessionId: j['session_id'] as String?,
          requestId: j['request_id'] as String?,
        ),
      _ => null, // evento novo no servidor: ignore com segurança
    };
  }
}

class StartEvent extends AgentEvent {
  final String sessionId, provider, model;
  const StartEvent({
    required this.sessionId,
    required this.provider,
    required this.model,
  });
}

class TokenEvent extends AgentEvent {
  final String content;
  const TokenEvent(this.content);
}

class ToolEvent extends AgentEvent {
  final String? name;
  const ToolEvent(this.name);

  /// Rótulo para o indicador de progresso. name pode vir null.
  String get rotulo => switch (name) {
        'cotacao_atual' || 'get_current_stock_price' => 'Consultando cotação…',
        'historico_precos' ||
        'get_historical_stock_prices' =>
          'Buscando histórico…',
        'resumo_financeiro' ||
        'get_stock_fundamentals' ||
        'get_key_financial_ratios' =>
          'Lendo indicadores…',
        'historico_dividendos' => 'Verificando dividendos…',
        'noticias_do_ativo' || 'get_company_news' => 'Lendo notícias…',
        'buscar_ativos' => 'Procurando o ativo…',
        'adicionar_a_watchlist' => 'Atualizando sua watchlist…',
        'remover_da_watchlist' => 'Atualizando sua watchlist…',
        _ => 'Pesquisando…',
      };
}

class DoneEvent extends AgentEvent {
  final String sessionId, provider, model, content;
  const DoneEvent({
    required this.sessionId,
    required this.provider,
    required this.model,
    required this.content,
  });
}

class ErrorEvent extends AgentEvent {
  final String detail;
  final String? sessionId;

  /// Mesmo id que aparece no log do servidor. Mostre na tela de erro:
  /// é o que permite localizar o traceback exato desta falha.
  final String? requestId;

  const ErrorEvent({required this.detail, this.sessionId, this.requestId});

  String get mensagemParaUsuario => requestId == null
      ? detail
      : '$detail (cód. $requestId)';
}

// ------------------------------------------------------------- cliente

class AgenteStreamApi {
  AgenteStreamApi({
    required this.baseUrl,
    required this.getToken,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final String Function() getToken;
  final http.Client _client;

  void dispose() => _client.close();

  Stream<AgentEvent> conversar({
    required String message,
    String? sessionId,
  }) async* {
    final request = http.Request('POST', Uri.parse('$baseUrl/ai/chat/stream'))
      ..headers.addAll({
        'Authorization': 'Bearer ${getToken()}',
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'text/event-stream',
      })
      ..body = jsonEncode({
        'message': message,
        if (sessionId != null) 'session_id': sessionId,
      });

    final response = await _client.send(request);

    // Erros de verdade (401/404/422) chegam ANTES do stream abrir.
    if (response.statusCode != 200) {
      final corpo = await response.stream.bytesToString();
      throw ApiException.fromResponse(response.statusCode, corpo);
    }

    String? nomeEvento;
    final linhasDeDados = <String>[];

    // utf8.decoder como transformer guarda estado entre chunks: um caractere
    // acentuado partido no meio de dois pacotes é remontado corretamente.
    final linhas = response.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter());

    await for (final linha in linhas) {
      // Linha em branco fecha o frame.
      if (linha.isEmpty) {
        if (nomeEvento != null && linhasDeDados.isNotEmpty) {
          final evento = AgentEvent.parse(nomeEvento, linhasDeDados.join('\n'));
          if (evento != null) yield evento;
        }
        nomeEvento = null;
        linhasDeDados.clear();
        continue;
      }
      if (linha.startsWith(':')) continue; // comentário/keep-alive do SSE
      if (linha.startsWith('event:')) {
        nomeEvento = linha.substring(6).trim();
      } else if (linha.startsWith('data:')) {
        // Um único espaço após 'data:' faz parte do protocolo e é descartado;
        // qualquer outro espaço é conteúdo e precisa ser preservado.
        var valor = linha.substring(5);
        if (valor.startsWith(' ')) valor = valor.substring(1);
        linhasDeDados.add(valor);
      }
    }

    // Frame final sem linha em branco no fim: emite mesmo assim.
    if (nomeEvento != null && linhasDeDados.isNotEmpty) {
      final evento = AgentEvent.parse(nomeEvento, linhasDeDados.join('\n'));
      if (evento != null) yield evento;
    }
  }
}
```

> **Por que não usar timeout total no streaming:** um `.timeout()` no stream inteiro cancela respostas longas legítimas. Se precisar de proteção, aplique um timeout **por evento** (`stream.timeout(const Duration(seconds: 60))` dispara quando fica 60 s *sem nenhum evento*), que é o comportamento certo: detecta conexão morta sem punir resposta demorada.

---

## Uso na tela

Controller mínimo consumindo o stream, com as regras de terminação já aplicadas. Vale para `ChangeNotifier`, Bloc ou Riverpod — o miolo é o mesmo.

```dart
// lib/agente/chat_controller.dart
import 'dart:async';
import 'package:flutter/foundation.dart';

import 'agente_stream.dart';
import 'models.dart';

class ChatController extends ChangeNotifier {
  ChatController(this._api);

  final AgenteStreamApi _api;
  StreamSubscription<AgentEvent>? _sub;

  String? sessionId;
  String textoParcial = '';
  String? ferramentaAtual; // rótulo do indicador "consultando…"
  String? erro;
  bool respondendo = false;
  bool watchlistPodeTerMudado = false;

  Future<void> enviar(String mensagem) async {
    if (respondendo) return;

    respondendo = true;
    textoParcial = '';
    ferramentaAtual = null;
    erro = null;
    watchlistPodeTerMudado = false;
    notifyListeners();

    // done é o ÚNICO terminador legítimo. Fechar sem ele = erro fatal.
    var terminouLimpo = false;
    String? ultimoErro;

    _sub = _api
        .conversar(message: mensagem, sessionId: sessionId)
        // Sem eventos por 60s = conexão morta. Não limita a duração total.
        .timeout(const Duration(seconds: 60))
        .listen(
      (evento) {
        switch (evento) {
          case StartEvent(sessionId: final novoId):
            // Persista JÁ: se o app fechar no meio, a conversa não se perde.
            sessionId = novoId;

          case TokenEvent(:final content):
            ferramentaAtual = null;
            textoParcial += content;

          case ToolEvent():
            ferramentaAtual = evento.rotulo;
            if (evento.name == 'adicionar_a_watchlist' ||
                evento.name == 'remover_da_watchlist') {
              watchlistPodeTerMudado = true;
            }

          case DoneEvent(:final content):
            // content traz a resposta inteira: mais confiável que a concatenação.
            textoParcial = content;
            ferramentaAtual = null;
            terminouLimpo = true;

          case ErrorEvent():
            // Guarda com o request_id junto: é o que o usuário reporta.
            ultimoErro = evento.mensagemParaUsuario;
        }
        notifyListeners();
      },
      onError: (e) {
        erro = e is ApiException ? e.mensagemAmigavel : 'Falha de conexão.';
        respondendo = false;
        notifyListeners();
      },
      onDone: () {
        // Fechou sem done: o último error era fatal.
        if (!terminouLimpo) {
          erro = ultimoErro ?? 'A resposta foi interrompida.';
        }
        respondendo = false;
        notifyListeners();
      },
      cancelOnError: true,
    );
  }

  void cancelar() {
    _sub?.cancel();
    _sub = null;
    respondendo = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
```

### Renderizando a resposta

O conteúdo é Markdown com tabelas. Adicione `flutter_markdown` ao `pubspec.yaml` e habilite a extensão de tabelas — sem ela, a comparação de indicadores que o agente monta aparece como texto com barras verticais.

```dart
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:markdown/markdown.dart' as md;

MarkdownBody(
  data: controller.textoParcial,
  selectable: true,
  extensionSet: md.ExtensionSet.gitHubWeb, // habilita tabelas
  onTapLink: (text, href, title) {
    if (href != null) launchUrlString(href);
  },
)
```

---

## Tabela de erros

| Código | Formato de `detail` | Causa | O que o app faz |
|---|---|---|---|
| `401` | `string` | Token ausente, malformado ou expirado (1h) | Tentar relogar uma vez; se falhar, ir para a tela de login |
| `404` | `string` | Conversa inexistente ou de outro usuário | Remover da lista local e voltar para o histórico |
| `422` | `array` | Mensagem vazia ou > 4000 caracteres | Validar antes de enviar; barrar no `TextField` com `maxLength` |
| `502` | `string` | Gemini e Groq falharam | Mostrar aviso e oferecer "tentar de novo" — costuma ser transitório |
| `200` | evento `error` | Falha depois do stream ter aberto | Tratar dentro do stream; status HTTP não indica o problema |

---

## Armadilhas

Checklist antes de considerar a integração pronta.

- [ ] **Login é form-urlencoded com `username`.** Não é JSON e o campo não se chama `email`.
- [ ] **Emulador Android usa `10.0.2.2`.** `localhost` aponta para o próprio emulador. No simulador iOS, `localhost` funciona.
- [ ] **HTTP em claro é bloqueado por padrão.** Para apontar o app para `http://` em desenvolvimento, configure `usesCleartextTraffic` no Android e ATS no iOS — ou use HTTPS.
- [ ] **Use `utf8.decode(bodyBytes)`, nunca `response.body`.** O `.body` assume latin-1 quando o charset não vem declarado, e todo acento do português vira caractere quebrado.
- [ ] **DELETE responde 204 sem corpo.** `jsonDecode` de corpo vazio lança exceção.
- [ ] **`summary` e `topics` vêm vazios em conversas novas.** O resumo só nasce depois de algumas trocas — sempre tenha fallback no título da lista.
- [ ] **Timestamps têm dois formatos.** Int unix em `/ai/sessions` e nas mensagens; string ISO 8601 no `updated_at` do summary.
- [ ] **Filtre `role` antes de renderizar.** O histórico contém mensagens `system` e `tool` que não devem chegar à tela.
- [ ] **`done` é o único terminador válido.** Stream fechado sem ele significa erro fatal, mesmo com HTTP 200.
- [ ] **Salve o `session_id` no evento `start`**, não no `done` — senão uma resposta interrompida perde a conversa inteira.
- [ ] **Cancele a subscription no `dispose()`.** Sair da tela no meio de uma resposta deixa a conexão aberta e o `notifyListeners()` disparando em widget morto.
- [ ] **Invalide a watchlist local** quando `tools_used` (ou um `ToolEvent`) trouxer `adicionar_a_watchlist` / `remover_da_watchlist`.
- [ ] **Feche o `http.Client`.** Um client por serviço, reaproveitado; `close()` no dispose.
- [ ] **Mostre o `request_id` na mensagem de erro.** Vem no campo `request_id` do frame `error`, no header `X-Request-ID` de toda resposta e no fim do `detail` dos 502. É o que liga o print do usuário ao traceback no servidor.
- [ ] **Opcional: envie seu próprio `X-Request-ID`.** Se o app gerar o id e mandar no header, a API o reaproveita — aí o mesmo id fica no log do app e no do servidor.

> **Testando sem o app:** `http://localhost:8000/docs` tem o Swagger UI com todos os endpoints. Clique em **Authorize**, faça login lá mesmo e dispare as chamadas — é a forma mais rápida de conferir um payload antes de escrever o widget.

---

*Contrato conferido em 14/08/2026 · API Financeira · Agno 2.9 · FastAPI*
