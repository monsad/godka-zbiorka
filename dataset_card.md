---
license: cc0-1.0
language:
- szl
- pl
pretty_name: Zbiórka gŏdki
task_categories:
- text-generation
- automatic-speech-recognition
- translation
size_categories:
- n<1K
configs:
- config_name: teksty
  data_files: "data/teksty-*.jsonl"
- config_name: nagrania
  data_files: "data/nagrania-*.jsonl"
- config_name: poprawki
  data_files: "data/poprawki-*.jsonl"
---

# Zbiórka gŏdki

Śląska gŏdka zbierana od ludzi przez stronę
[Zbiórka gŏdki](https://github.com/monsad/godka-zbiorka) — do douczania
modelu Bielik i innych modeli dla języka śląskiego. Zbiór rośnie na bieżąco
(nowe zgłoszenia co kilka minut).

## Zawartość

| plik | pola |
|---|---|
| `data/teksty-*.jsonl` | `id`, `czas`, `tekst`, `miejscowosc` |
| `data/nagrania-*.jsonl` | `id`, `czas`, `zdanie_id`, `zdanie`, `plik`, `sekundy`, `miejscowosc` |
| `data/nagrania/*.wav` | nagrania mono 16-bit PCM |
| `data/poprawki-*.jsonl` | `id`, `czas`, `pl`, `bielik`, `poprawka`, `miejscowosc` |

`miejscowosc` jest opcjonalna i podawana przez autora zgłoszenia. Pisownia tekstów jest
dowolna (Ślabikŏrz, Steuer, „po polsku”).

## Licencja i pochodzenie

- Zgłoszenia są udostępniane przez autorów na licencji **CC0 1.0**.
- Zdania czytane w nagraniach pochodzą ze
  [ślōnskij Wikipedyje](https://szl.wikipedia.org) (CC BY-SA 4.0); pole `zdanie`
  podlega tej licencji.
- Pole `bielik` to automatyczne tłumaczenie modelu Bielik (z adapterem śląskim) —
  bywa błędne; wartością jest pole `poprawka`.

## Ograniczenia

Zbiór nie jest moderowany na bieżąco. Może zawierać błędy, nagrania słabej jakości
albo pojedyncze śmieci. Zgłoszenia z danymi osobowymi są usuwane po wykryciu.
