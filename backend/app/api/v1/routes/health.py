from fastapi import APIRouter


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    # 最简单的健康检查接口，用于确认服务进程是否正常启动。
    return {"status": "ok"}
