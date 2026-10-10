from result_labels import federated_method_label


def test_federated_result_label_distinguishes_institution_privacy():
    assert federated_method_label(True) == "fedavg_institution_privacy"
    assert federated_method_label(False) == "fedavg"
