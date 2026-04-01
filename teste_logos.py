import yfinance as yf


def pegar_link_logo(ticker_nome):
    try:
        # 1. Acessa os dados do ativo
        ativo = yf.Ticker(ticker_nome)
        info = ativo.info

        # 2. Pega o site (ex: https://www.nvidia.com)
        site = info.get('website')

        if not site:
            return f"Site não encontrado para {ticker_nome}"

        # 3. Limpa a URL para deixar apenas o domínio (nvidia.com)
        dominio = site.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]

        # 4. Monta a URL do FaviconGrabber (ou da Clearbit que é mais direta para imagens)
        # O FaviconGrabber retorna um JSON, se quiser o link direto da imagem,
        # a Clearbit ou o Google Favicon são mais simples para Python:
        link_logo = f"https://www.google.com/s2/favicons?domain={dominio}&sz=128"

        return link_logo

    except Exception as e:
        return f"Erro ao processar {ticker_nome}: {e}"


# --- TESTANDO COM VÁRIOS ATIVOS ---
lista_ativos = ["NVDA", "BBDC4.SA", "ITUB4.SA", "AAPL", "PETR4.SA"]

print("Gerando links de ícones:\n")
for ticker in lista_ativos:
    url = pegar_link_logo(ticker)
    print(f"{ticker}: {url}")