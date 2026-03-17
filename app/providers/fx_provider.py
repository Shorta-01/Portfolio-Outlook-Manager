from app.providers.fallback_provider import FallbackProvider
from app.providers.manual_provider import ManualProvider
from app.providers.twelve_data_provider import TwelveDataProvider


# Dedicated FX provider chain for forward compatibility.
FXProvider = FallbackProvider


def build_fx_provider(manual_provider: ManualProvider) -> FXProvider:
    return FXProvider([TwelveDataProvider(), manual_provider])
