from fastapi import APIRouter, Depends

from app.dna_connect.auth.dependencies import get_current_user
from app.dna_connect.dashboard.service import obter_resumo_dashboard

router = APIRouter()


@router.get("/dashboard")
def get_dashboard(current_user=Depends(get_current_user)):
    """
    Retorna o resumo do Dashboard do usuário autenticado.
    """

    return obter_resumo_dashboard(current_user)
