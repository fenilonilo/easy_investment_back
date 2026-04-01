from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from infrastructure.database import get_db
from models.user import User, UserCreate, UserResponse, UserUpdate
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/user", tags=["User"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
        user: UserCreate,
        db: Session = Depends(get_db),
        # Descomente a linha abaixo se quiser que APENAS usuários logados criem outros
        # current_user: User = Depends(get_current_user)
):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="E-mail já registrado.")

    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=get_password_hash(user.password),
        birth_date=user.birth_date,
        investor_profile=user.investor_profile
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.delete("/delete/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_user)])
def delete_user(
        user_id: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)  # Exige login
):
    # Proteção: Um usuário comum só pode deletar a si mesmo?
    # Se sim, validamos se o ID do token é igual ao ID da URL
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para deletar este usuário."
        )

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    db.delete(db_user)
    db.commit()
    return


@router.put("/update/{user_id}", status_code=status.HTTP_200_OK, dependencies=[Depends(get_current_user)])
def update_user(
        user_id: str,
        user_data: UserUpdate,  # Recebe o JSON com os novos dados
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Proteção: Garante que o usuário só edite o próprio perfil
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para atualizar este usuário."
        )

    # Busca o usuário no banco
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    update_data = user_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.commit()
    db.refresh(db_user)

    return db_user