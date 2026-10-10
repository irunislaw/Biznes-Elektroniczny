# Zasady pracy w repozytorium 
- Nigdy nie pushujemy na main i nie robimy force push. Każda zmiana: ticket w Jira -> issue na GitHubie -> gałąź -> PR -> recenzja -> scalenie
- Bez issue na Githubie nie ma ticketu. Dla prowadzącego bo oni chcą issues mieć
- Gałąź i PR zaczynają się od klucza z Jiry a opis PR zawiera Closes #34 z numerem issue z Githbua
- recenzja zawiera merytoryczny komentarz a nie samo LGTM bo prowadzący to sprawdza
- Do odbiora każy musi mieć 3 scalone PR jako autor i 3 jako recenzent
- Sekrety tylko w .env w repozytorium jest tylko .env.example 
- AI: jeśli PR zawiera instosny kod z AI dostaje etykietę ai-assisted w opisie piszemy jak sprawdziliśmy poprawność, a w tym samym PR dopisujemy wiersz w docs/AI_LOG.md. Minimum 2 wpisyna osobę w całym etapie
# kamienie milowe
- 12-13.10 sklep źródłowy wybrany, zadania przypisane
- 14.10 wszyscy maja dostęp do Jira i repo, main chroniony, każdy otworzył issues dla swoich ticketów
- 16.10: sklep startuje z deploy/compose.yaml u conajmniej dwóch osób 
- 19.10, check-in: kto ma już coś działającego, kto potrzebuje pomocy, czy CI działa 
- 21.10 wszystkie PR otwarte 
- 23.19 wszystko sprawdzone i zmergowane weekend zostaje jako zapas 
