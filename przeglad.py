"""Przegląd zgłoszeń: prywatna skrzynka -> publiczny zbiór.

    python przeglad.py

Pobiera prywatną skrzynkę (zbiór, do którego pisze strona), pokazuje po kolei zgłoszenia,
których jeszcze nie oceniono, i wysyła zatwierdzone do zbioru publicznego.
Decyzje zapisuje w skrzynce (`decyzje/*.jsonl`), więc nic nie jest oceniane dwa razy.
Wymaga zalogowania do HF (`hf auth login`) na konto z prawem zapisu do obu zbiorów.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKRZYNKA = "mosad2024/szl-godka-zbiorka"
PUBLICZNY = "mosad2024/szl-godka"
RODZAJE = ("teksty", "nagrania", "poprawki")


# --- logika (bez sieci, testowana) ---

def wczytaj_zgloszenia(folder: Path) -> list[dict]:
    """Wszystkie zgłoszenia ze skrzynki, od najstarszego; każde z polem `rodzaj`."""
    wynik = []
    for rodzaj in RODZAJE:
        for plik in sorted((Path(folder) / "data").glob(f"{rodzaj}-*.jsonl")):
            for linia in plik.read_text(encoding="utf-8").splitlines():
                if linia.strip():
                    wynik.append({"rodzaj": rodzaj, **json.loads(linia)})
    return sorted(wynik, key=lambda z: z["czas"])


def wczytaj_decyzje(folder: Path) -> dict[str, str]:
    """id -> "tak"/"nie"; przy powtórce wygrywa późniejsza decyzja."""
    decyzje = {}
    for plik in sorted((Path(folder) / "decyzje").glob("*.jsonl")):
        for linia in plik.read_text(encoding="utf-8").splitlines():
            if linia.strip():
                d = json.loads(linia)
                decyzje[d["id"]] = d["decyzja"]
    return decyzje


def do_oceny(zgloszenia: list[dict], decyzje: dict[str, str]) -> list[dict]:
    return [z for z in zgloszenia if z["id"] not in decyzje]


def przygotuj_publiczne(zatwierdzone: list[dict], skrzynka: Path, cel: Path, znacznik: str) -> None:
    """Zapisuje zatwierdzone do folderu `cel` w układzie zbioru publicznego.

    Każdy przegląd dostaje własne pliki `data/<rodzaj>-<znacznik>.jsonl`, więc nic
    wcześniej opublikowanego nie jest nadpisywane.
    """
    for rodzaj in RODZAJE:
        wiersze = [{k: v for k, v in z.items() if k != "rodzaj"} for z in zatwierdzone if z["rodzaj"] == rodzaj]
        if not wiersze:
            continue
        (cel / "data").mkdir(parents=True, exist_ok=True)
        with (cel / "data" / f"{rodzaj}-{znacznik}.jsonl").open("w", encoding="utf-8") as f:
            for w in wiersze:
                f.write(json.dumps(w, ensure_ascii=False) + "\n")
        if rodzaj == "nagrania":
            for w in wiersze:
                zrodlo = Path(skrzynka) / "data" / w["plik"]
                docel = cel / "data" / w["plik"]
                docel.parent.mkdir(parents=True, exist_ok=True)
                docel.write_bytes(zrodlo.read_bytes())


def zapisz_decyzje(decyzje: dict[str, str], plik: Path) -> None:
    czas = datetime.now(timezone.utc).isoformat(timespec="seconds")
    plik.parent.mkdir(parents=True, exist_ok=True)
    with plik.open("w", encoding="utf-8") as f:
        for id_, d in decyzje.items():
            f.write(json.dumps({"id": id_, "decyzja": d, "czas": czas}) + "\n")


# --- terminal ---

def pokaz(z: dict, skrzynka: Path) -> None:
    print("\n" + "─" * 60)
    print(f"[{z['rodzaj']}] {z['czas']}  miejscowość: {z.get('miejscowosc') or '—'}")
    if z["rodzaj"] == "teksty":
        print(z["tekst"])
    elif z["rodzaj"] == "poprawki":
        print(f"PL:      {z['pl']}\nBielik:  {z['bielik']}\nPoprawka: {z['poprawka']}")
    else:
        print(f"Zdanie: {z['zdanie']}  ({z['sekundy']} s)")
        odtworz(skrzynka / "data" / z["plik"])


def odtworz(plik: Path) -> None:
    try:
        subprocess.run(["afplay", str(plik)], check=False)
    except FileNotFoundError:
        print(f"(brak afplay — posłuchaj ręcznie: {plik})")


def zapytaj(z: dict, skrzynka: Path) -> str:
    opcje = "[t]ak / [n]ie / [p]omiń / " + ("[o]dtwórz / " if z["rodzaj"] == "nagrania" else "") + "[q] koniec: "
    while True:
        odp = input(opcje).strip().lower()
        if odp == "o" and z["rodzaj"] == "nagrania":
            odtworz(skrzynka / "data" / z["plik"])
        elif odp in ("t", "n", "p", "q"):
            return odp


def main() -> None:
    from huggingface_hub import CommitOperationAdd, HfApi, snapshot_download

    api = HfApi()
    print(f"Pobieram skrzynkę {SKRZYNKA}…")
    skrzynka = Path(snapshot_download(SKRZYNKA, repo_type="dataset"))
    kolejka = do_oceny(wczytaj_zgloszenia(skrzynka), wczytaj_decyzje(skrzynka))
    print(f"Do oceny: {len(kolejka)}")

    nowe: dict[str, str] = {}
    try:
        for i, z in enumerate(kolejka, 1):
            print(f"\n({i}/{len(kolejka)})", end="")
            pokaz(z, skrzynka)
            odp = zapytaj(z, skrzynka)
            if odp == "q":
                break
            if odp in ("t", "n"):
                nowe[z["id"]] = "tak" if odp == "t" else "nie"
    except (KeyboardInterrupt, EOFError):
        print("\nPrzerwano — zapisuję to, co już ocenione.")

    if not nowe:
        print("Nic nie oceniono.")
        return

    znacznik = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    zatwierdzone = [z for z in kolejka if nowe.get(z["id"]) == "tak"]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if zatwierdzone:
            przygotuj_publiczne(zatwierdzone, skrzynka, tmp / "pub", znacznik)
            api.upload_folder(repo_id=PUBLICZNY, repo_type="dataset", folder_path=tmp / "pub",
                              commit_message=f"Przegląd {znacznik}: +{len(zatwierdzone)}")
        zapisz_decyzje(nowe, tmp / "decyzje.jsonl")
        api.create_commit(SKRZYNKA, repo_type="dataset", commit_message=f"Decyzje {znacznik}",
                          operations=[CommitOperationAdd(f"decyzje/{znacznik}.jsonl", tmp / "decyzje.jsonl")])
    odrzucone = sum(d == "nie" for d in nowe.values())
    print(f"Gotowe: opublikowano {len(zatwierdzone)}, odrzucono {odrzucone}.")


if __name__ == "__main__":
    main()
