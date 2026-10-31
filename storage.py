"""Walidacja i zapis zgłoszeń do lokalnego folderu, który CommitScheduler wysyła na Hugging Face.

Pliki są tylko dopisywane (append-only), jeden zestaw na sesję Space'a,
więc restart nigdy nie nadpisze wcześniejszych danych.
"""
from __future__ import annotations

import io
import json
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

TEKST_MIN, TEKST_MAX = 10, 5000
NAGRANIE_MIN_S, NAGRANIE_MAX_S = 1.0, 30.0
MIEJSCOWOSC_MAX = 100


class BladZgloszenia(ValueError):
    """Zgłoszenie odrzucone; komunikat jest dla użytkownika."""


class Zbior:
    def __init__(self, folder: Path, lock, sesja: str | None = None):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock = lock
        self.sesja = sesja or uuid.uuid4().hex[:12]

    # --- publiczne ---

    def zapisz_tekst(self, tekst: str, miejscowosc: str, zgoda: bool) -> None:
        self._sprawdz_zgode(zgoda)
        tekst = (tekst or "").strip()
        if not TEKST_MIN <= len(tekst) <= TEKST_MAX:
            raise BladZgloszenia(f"Tekst musi mieć od {TEKST_MIN} do {TEKST_MAX} znaków.")
        self._dopisz("teksty", {"tekst": tekst, "miejscowosc": _miejscowosc(miejscowosc)})

    def zapisz_nagranie(self, audio, zdanie_id: str, zdanie: str, miejscowosc: str, zgoda: bool) -> None:
        self._sprawdz_zgode(zgoda)
        if audio is None:
            raise BladZgloszenia("Najpierw nagraj zdanie.")
        sr, dane = audio
        dane = _do_mono_int16(np.asarray(dane))
        sekundy = round(len(dane) / sr, 2)
        if not NAGRANIE_MIN_S <= sekundy <= NAGRANIE_MAX_S:
            raise BladZgloszenia(
                f"Nagranie musi trwać od {NAGRANIE_MIN_S:g} do {NAGRANIE_MAX_S:g} s (masz {sekundy:g} s).")
        id_ = uuid.uuid4().hex
        plik = Path("nagrania") / f"{id_}.wav"
        with self.lock:
            (self.folder / "nagrania").mkdir(exist_ok=True)
            with wave.open(str(self.folder / plik), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(int(sr))
                f.writeframes(dane.tobytes())
        self._dopisz("nagrania", {"zdanie_id": zdanie_id, "zdanie": zdanie, "plik": plik.as_posix(),
                                  "sekundy": sekundy, "miejscowosc": _miejscowosc(miejscowosc)}, id_=id_)

    def zapisz_poprawke(self, pl: str, bielik: str, poprawka: str, miejscowosc: str, zgoda: bool) -> None:
        self._sprawdz_zgode(zgoda)
        poprawka = (poprawka or "").strip()
        if not poprawka:
            raise BladZgloszenia("Wpisz poprawioną wersję po śląsku.")
        if len(poprawka) > TEKST_MAX:
            raise BladZgloszenia(f"Poprawka może mieć najwyżej {TEKST_MAX} znaków.")
        self._dopisz("poprawki", {"pl": pl, "bielik": bielik, "poprawka": poprawka,
                                  "miejscowosc": _miejscowosc(miejscowosc)})

    # --- wewnętrzne ---

    @staticmethod
    def _sprawdz_zgode(zgoda: bool) -> None:
        if not zgoda:
            raise BladZgloszenia("Zaznacz zgodę na udostępnienie na licencji CC0.")

    def _dopisz(self, rodzaj: str, pola: dict, id_: str | None = None) -> None:
        wiersz = {"id": id_ or uuid.uuid4().hex,
                  "czas": datetime.now(timezone.utc).isoformat(timespec="seconds"), **pola}
        with self.lock:
            with (self.folder / f"{rodzaj}-{self.sesja}.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(wiersz, ensure_ascii=False) + "\n")


def wav_do_numpy(dane: bytes) -> tuple[int, np.ndarray]:
    """WAV z mikrofonu w przeglądarce -> (częstotliwość, próbki); stereo jako tablica (n, kanały)."""
    typy = {1: np.uint8, 2: np.int16, 4: np.int32}
    try:
        with wave.open(io.BytesIO(dane)) as f:
            sr, kanaly, szer = f.getframerate(), f.getnchannels(), f.getsampwidth()
            ramki = f.readframes(f.getnframes())
    except (wave.Error, EOFError) as e:
        raise BladZgloszenia("Nie udało się odczytać nagrania. Spróbuj nagrać jeszcze raz.") from e
    if szer not in typy:
        raise BladZgloszenia("Nieobsługiwany format nagrania.")
    probki = np.frombuffer(ramki, dtype=typy[szer])
    if szer == 1:
        probki = (probki.astype(np.int16) - 128) * 256
    return sr, probki.reshape(-1, kanaly) if kanaly > 1 else probki


def _miejscowosc(m: str) -> str:
    return (m or "").strip()[:MIEJSCOWOSC_MAX]


def _do_mono_int16(dane: np.ndarray) -> np.ndarray:
    if dane.ndim == 2:
        dane = dane.mean(axis=1)
    if np.issubdtype(dane.dtype, np.floating):
        dane = np.clip(dane, -1.0, 1.0) * 32767
    elif dane.dtype == np.int32:
        dane = dane / 65536
    return dane.astype(np.int16)
