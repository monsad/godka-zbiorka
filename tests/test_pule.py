import json

from pule import Pula


def zapisz(path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def test_losuje_z_puli(tmp_path):
    zapisz(tmp_path / "zdania.jsonl", [{"id": "a", "zdanie": "Jedyn."}, {"id": "b", "zdanie": "Dwa."}])
    pula = Pula.z_pliku(tmp_path / "zdania.jsonl")
    assert len(pula) == 2
    assert pula.losuj()["id"] in {"a", "b"}


def test_losuje_inne_niz_poprzednie(tmp_path):
    zapisz(tmp_path / "zdania.jsonl", [{"id": "a", "zdanie": "Jedyn."}, {"id": "b", "zdanie": "Dwa."}])
    pula = Pula.z_pliku(tmp_path / "zdania.jsonl")
    for _ in range(20):
        assert pula.losuj(poprzednie="a")["id"] == "b"


def test_brak_pliku_daje_pusta_pule(tmp_path):
    pula = Pula.z_pliku(tmp_path / "nie_ma.jsonl")
    assert len(pula) == 0 and pula.losuj() is None
