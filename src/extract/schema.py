"""LLM'in ilandan çıkaracağı yapılandırılmış alanlar."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.data.models import ParcaDurumu, ParcaTipi


class ParcaCikti(BaseModel):
    tip: ParcaTipi = Field(description="tavan, kaput, bagaj, kapi, camurluk veya tampon")
    durum: ParcaDurumu = Field(description="degisen, boyali veya lokal_boyali")
    konum: str = Field(description="ör. 'sol ön', 'arka'; yoksa boş metin")


class IlanBilgisi(BaseModel):
    marka: Optional[str] = Field(description="ör. Volkswagen, BMW, Mercedes-Benz")
    model: Optional[str] = Field(description="seri/model adı, motor ve paket olmadan; ör. Golf, 3 Serisi, C-Serisi, Egea")
    motor: Optional[str] = Field(description="motor hacmi ve tipi; ör. '1.6 TDI', '320i', '1.5 eTSI'")
    paket: Optional[str] = Field(description="donanım paketi; ör. Comfortline, Highline, M Sport, AMG")
    yil: Optional[int] = Field(description="model yılı")
    km: Optional[int]
    yakit: Optional[str] = Field(description="benzin, dizel, hibrit, elektrik veya lpg")
    vites: Optional[str] = Field(description="manuel veya otomatik")
    fiyat: Optional[int] = Field(description="ilan fiyatı, TL, tam sayı")
    parcalar: list[ParcaCikti] = Field(description="boyalı, lokal boyalı veya değişen parçalar")
    diger_parcalar: list[str] = Field(description="tabloda olmayan hasarlı parçalar (ör. marşpiyel, direk, şasi), serbest metin")
    parca_bilgisi_var: bool = Field(description="ilanda boya/değişen durumu hakkında herhangi bir bilgi var mı")
    agir_hasar: Optional[bool] = Field(description="ağır hasar kaydı var mı; belirtilmemişse null")
    tramer_tutari: Optional[int] = Field(description="TL; 'tramer yok' denmişse 0; belirtilmemişse null")
    satici_tipi: Optional[Literal["sahibinden", "galeri", "yetkili_bayi"]]
    belirsiz_alanlar: list[str] = Field(description="ilandan net anlaşılamayan alanların adları")
    celiskiler: list[str] = Field(description="ilanda birbiriyle çelişen bilgiler, kısa açıklama")
