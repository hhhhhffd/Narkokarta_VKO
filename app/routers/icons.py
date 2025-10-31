"""
Роутер для генерации SVG иконок меток
"""
from fastapi import APIRouter, Response
from fastapi.responses import Response as FastAPIResponse


router = APIRouter(prefix="/image", tags=["Icons"])


def generate_marker_svg(color: str, emoji: str = "📍") -> str:
    """
    Генерирует SVG для иконки метки
    """
    return f"""<svg width="40" height="40" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.3"/>
    </filter>
  </defs>
  <circle cx="20" cy="20" r="18" fill="{color}" stroke="#ffffff" stroke-width="3" filter="url(#shadow)"/>
  <text x="20" y="26" font-size="16" text-anchor="middle" fill="#ffffff">{emoji}</text>
</svg>"""


def generate_cluster_svg() -> str:
    """
    Генерирует SVG для кластерной метки
    """
    return """<svg width="50" height="50" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
      <feDropShadow dx="0" dy="2" stdDeviation="4" flood-opacity="0.4"/>
    </filter>
  </defs>
  <circle cx="25" cy="25" r="23" fill="#9b59b6" stroke="#ffffff" stroke-width="4" filter="url(#shadow)"/>
  <circle cx="25" cy="25" r="18" fill="none" stroke="#ffffff" stroke-width="2" opacity="0.5"/>
</svg>"""


@router.get("/icon1")
async def icon1():
    """Притон - красный"""
    svg = generate_marker_svg("#dc3545", "🏚")
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/icon2")
async def icon2():
    """Реклама - оранжевый"""
    svg = generate_marker_svg("#fd7e14", "📢")
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/icon3")
async def icon3():
    """Курьер - желтый"""
    svg = generate_marker_svg("#ffc107", "🚶")
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/icon4")
async def icon4():
    """Употребление - зеленый"""
    svg = generate_marker_svg("#28a745", "💊")
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/icon5")
async def icon5():
    """Мусор - белый/серый"""
    svg = generate_marker_svg("#6c757d", "🗑")
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/icon6")
async def icon6():
    """Кластер - фиолетовый"""
    svg = generate_cluster_svg()
    return Response(content=svg, media_type="image/svg+xml")
