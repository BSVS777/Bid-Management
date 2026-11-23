import pytest

from app.services import suppliers as svc

P1 = "Tecnología Norte S.A."
P2 = "Servicios del Valle"


def test_normalize_trims_and_collapses_whitespace():
    assert svc.normalize_name("  Servicios   del \t Valle  ") == P2


@pytest.mark.parametrize("name", [P1, P2, "Café Ñandú (Sur), Ltda.", "Proveedor 24", "A"])
def test_valid_names_are_accepted(name):
    assert svc.validate_name(name) == name


@pytest.mark.parametrize(
    "name",
    ["<script>alert(1)</script>", "A<B", "A>B", "A;B", "A'B", 'A"B', "A&B",
     "A/B", "A@B", "A#B", "A$B", "A%B", "A_B", "A-B", "A\\B"],
)
def test_disallowed_characters_are_rejected(name):
    with pytest.raises(svc.InvalidSupplierError):
        svc.validate_name(name)


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_blank_name_is_rejected(name):
    with pytest.raises(svc.InvalidSupplierError):
        svc.validate_name(name)


@pytest.mark.parametrize("value", [None, 123, ["a"], {"a": 1}])
def test_non_string_is_rejected(value):
    with pytest.raises(svc.InvalidSupplierError):
        svc.validate_name(value)


def test_length_limit():
    assert svc.validate_name("a" * 120) == "a" * 120
    with pytest.raises(svc.InvalidSupplierError):
        svc.validate_name("a" * 121)


def test_length_is_measured_after_normalization():
    assert svc.validate_name("  " + "a" * 120 + "   ") == "a" * 120


def test_create_stores_normalized_name(session):
    supplier = svc.create_supplier(session, "  Servicios   del Valle ")
    assert supplier.id is not None
    assert supplier.name == P2


@pytest.mark.parametrize("variant", ["  TECNOLOGÍA   norte s.a. ", "tecnología norte s.a.", P1])
def test_duplicate_variants_are_rejected(session, variant):
    svc.create_supplier(session, P1)
    with pytest.raises(svc.DuplicateSupplierError):
        svc.create_supplier(session, variant)
    assert len(svc.list_suppliers(session)) == 1


def test_list_is_ordered_by_id(session):
    svc.create_supplier(session, P2)
    svc.create_supplier(session, P1)
    assert [s.name for s in svc.list_suppliers(session)] == [P2, P1]


def test_get_unknown_raises(session):
    with pytest.raises(svc.SupplierNotFoundError):
        svc.get_supplier(session, 999)


def test_update_changes_name(session):
    s = svc.create_supplier(session, P2)
    updated = svc.update_supplier(session, s.id, "Servicios del Valle Norte")
    assert updated.name == "Servicios del Valle Norte"


def test_update_to_case_variant_of_itself_is_allowed(session):
    s = svc.create_supplier(session, P1)
    updated = svc.update_supplier(session, s.id, "  TECNOLOGÍA  NORTE S.A.  ")
    assert updated.name == "TECNOLOGÍA NORTE S.A."


def test_update_colliding_with_other_is_duplicate(session):
    svc.create_supplier(session, P1)
    other = svc.create_supplier(session, P2)
    with pytest.raises(svc.DuplicateSupplierError):
        svc.update_supplier(session, other.id, " tecnología NORTE s.a.")
    assert svc.get_supplier(session, other.id).name == P2


def test_update_invalid_and_unknown(session):
    s = svc.create_supplier(session, P1)
    with pytest.raises(svc.InvalidSupplierError):
        svc.update_supplier(session, s.id, "<b>x</b>")
    with pytest.raises(svc.SupplierNotFoundError):
        svc.update_supplier(session, 999, P2)
