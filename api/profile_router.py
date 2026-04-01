from typing import List
from sqlalchemy.orm import Session
from core.security import get_current_user
from infrastructure.database import get_db
from models.asset import Asset, AssetRemove
from models.user import User, UserWatchlist
from sqlalchemy.orm.attributes import flag_modified
from fastapi import APIRouter, Depends, HTTPException, status


router = APIRouter(prefix="/profile", tags=["Profile"], dependencies=[Depends(get_current_user)])


@router.post("/watchlist/add", status_code=status.HTTP_200_OK)
def add_to_watchlist(
        assets: List[Asset],  # Agora aceita uma lista de Assets
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Busca a watchlist do usuário
    watchlist = db.query(UserWatchlist).filter(UserWatchlist.user_id == current_user.id).first()

    # Converte os objetos Pydantic para dicionários
    new_assets_dicts = [a.dict() for a in assets]

    # 2. Se não existir, cria uma nova com todos os ativos da lista
    if not watchlist:
        # Dica: remover duplicatas da própria lista enviada (caso o usuário mande o mesmo ticker 2x)
        unique_new_assets = {a['ticker']: a for a in new_assets_dicts}.values()

        new_watchlist = UserWatchlist(
            user_id=current_user.id,
            tickers=list(unique_new_assets)
        )
        db.add(new_watchlist)
    else:
        # 3. Se existir, mesclamos as listas evitando duplicatas
        current_tickers = watchlist.tickers or []
        existing_tickers_set = {item['ticker'] for item in current_tickers}

        added_count = 0
        for asset_dict in new_assets_dicts:
            if asset_dict['ticker'] not in existing_tickers_set:
                current_tickers.append(asset_dict)
                existing_tickers_set.add(asset_dict['ticker'])
                added_count += 1

        if added_count == 0:
            raise HTTPException(status_code=400, detail="Todos os ativos já estão na sua lista.")

        watchlist.tickers = current_tickers
        flag_modified(watchlist, "tickers")

    db.commit()
    return {"message": "Ativos processados com sucesso!", "added_count": len(new_assets_dicts)}


@router.post("/watchlist/remove", status_code=status.HTTP_200_OK)
def remove_from_watchlist(
        assets_to_remove: List[AssetRemove],  # Agora aceita uma lista
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Busca a watchlist do usuário
    watchlist = db.query(UserWatchlist).filter(UserWatchlist.user_id == current_user.id).first()

    if not watchlist or not watchlist.tickers:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist não encontrada ou já está vazia."
        )

    # 2. Criamos um set com os tickers que devem ser removidos (para busca rápida O(1))
    tickers_to_delete = {a.ticker for a in assets_to_remove}

    original_size = len(watchlist.tickers)

    # 3. Filtramos a lista mantendo apenas quem NÃO está nos tickers para deletar
    watchlist.tickers = [
        item for item in watchlist.tickers
        if item['ticker'] not in tickers_to_delete
    ]

    # 4. Verifica se algo foi realmente removido
    if len(watchlist.tickers) == original_size:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum dos ativos informados foi encontrado na sua lista."
        )

    # 5. Notifica o SQLAlchemy da mudança no JSONB e salva
    flag_modified(watchlist, "tickers")
    db.commit()

    return {
        "message": "Remoção processada com sucesso!",
        "removed_count": original_size - len(watchlist.tickers)
    }


@router.get("/watchlist", response_model=List[Asset], status_code=status.HTTP_200_OK)
def get_watchlists(db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):

    watchlist = db.query(UserWatchlist).filter(UserWatchlist.user_id == current_user.id).first()

    if not watchlist:
        return []

    return watchlist.tickers
