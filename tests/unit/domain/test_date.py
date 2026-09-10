from core.domain.date import Date


def test_depuis_jj_mm_aaaa() -> None:
    assert Date.depuis_jj_mm_aaaa("28.07.1993") == Date(1993, 7, 28)


def test_age_a_anniversaire_deja_passe() -> None:
    naissance = Date(2000, 7, 21)
    assert naissance.age_a(Date(2026, 8, 10)) == 26


def test_age_a_anniversaire_pas_encore_atteint() -> None:
    naissance = Date(2000, 12, 20)
    assert naissance.age_a(Date(2026, 8, 10)) == 25


def test_age_a_jour_anniversaire_exact() -> None:
    naissance = Date(2000, 8, 10)
    assert naissance.age_a(Date(2026, 8, 10)) == 26


def test_plus_un_an() -> None:
    assert Date(2026, 6, 30).plus_un_an() == Date(2027, 6, 30)


def test_ordre() -> None:
    assert Date(2025, 1, 1) < Date(2026, 1, 1)
    assert Date(2026, 1, 1) < Date(2026, 2, 1)
    assert Date(2026, 2, 1) < Date(2026, 2, 2)
