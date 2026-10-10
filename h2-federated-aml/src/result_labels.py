"""Labels used to distinguish federated result variants in output tables."""


def federated_method_label(institution_privacy_enabled: bool) -> str:
    return "fedavg_institution_privacy" if institution_privacy_enabled else "fedavg"
