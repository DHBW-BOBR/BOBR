from fastapi import APIRouter

router = APIRouter()


@router.post("/")
async def import_file():
    raise NotImplementedError
