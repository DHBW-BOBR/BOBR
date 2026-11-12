from fastapi import APIRouter

router = APIRouter()


@router.post("/{issue_id}/accept")
async def accept(issue_id: int):
    raise NotImplementedError


@router.post("/{issue_id}/reject")
async def reject(issue_id: int):
    raise NotImplementedError
