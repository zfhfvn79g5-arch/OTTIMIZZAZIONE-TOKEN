import pytest

from ottimizzazione_token.compression import (
    compress,
    normalize_whitespace,
    remove_duplicate_paragraphs,
    remove_html_comments,
)


def test_normalizza_spazi_e_righe_vuote():
    text = "Ciao    mondo   \n\n\n\n- voce\n  - sotto voce  \n"
    assert normalize_whitespace(text) == "Ciao mondo\n\n- voce\n  - sotto voce"


def test_codice_non_toccato():
    code = "```python\ndef f():\n    x  =  1\n\n\n\n    return x\n```"
    para = "Questo paragrafo è abbastanza lungo da contare    come duplicato."
    text = f"{para}\n\n{code}\n\n{para}"
    out = compress(text).text
    assert code in out
    # Motivo: il paragrafo ripetuto dopo il codice è un duplicato e viene rimosso.
    assert out.count("come duplicato") == 1


def test_rimuove_commenti_html():
    assert remove_html_comments("a <!-- nota\ninterna --> b") == "a  b"


def test_paragrafi_duplicati_ignorando_maiuscole_e_spazi():
    uno = "Rispondi sempre in italiano e in modo conciso."
    text = f"{uno}\n\nRegola  due.\n\n{uno.upper()}\n\nFine."
    assert remove_duplicate_paragraphs(text) == f"{uno}\n\nRegola  due.\n\nFine."


def test_paragrafi_brevi_ripetuti_mantenuti():
    text = "Esempio:\n\nprimo\n\nEsempio:\n\nsecondo"
    assert remove_duplicate_paragraphs(text) == text


def test_risultato_piu_corto_e_statistiche():
    text = "<!-- c -->\nA   b\n\n\n\nC d\n"
    result = compress(text)
    assert result.text == "A b\n\nC d"
    assert result.compressed_chars < result.original_chars
    assert result.chars_saved == len(text) - len(result.text)


def test_testo_gia_pulito_invariato():
    text = "Già pulito.\n\nSecondo paragrafo."
    assert compress(text).text == text


def test_testo_vuoto():
    assert compress("").text == ""


def test_tecnica_sconosciuta():
    with pytest.raises(ValueError, match="sconosciute"):
        compress("x", ["inventata"])


def test_solo_tecniche_scelte():
    assert compress("a    b\n\na    b", ["whitespace"]).text == "a b\n\na b"
