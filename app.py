from flask import Flask, render_template, session, request
import random

app = Flask(__name__)
app.secret_key = 'superfarmer_secret_key'

# Dane początkowe
STADO_GLOWNE = {
    'króliki': 58,
    'owce': 24,
    'świnie': 20,
    'krowy': 12,
    'konie': 6,
    'małe psy': 4,
    'duże psy': 2
}

TABELA_WYMIAN = {
    'króliki': {'owce': 6},           # 6 królików → 1 owca
    'owce': {'świnie': 2, 'małe psy': 1},  # 2 owce → 1 świnia | 1 owca → 1 mały pies
    'świnie': {'krowy': 3},           # 3 świnie → 1 krowa
    'krowy': {'konie': 2, 'duże psy': 1},  # 2 krowy → 1 koń | 1 krowa → 1 duży pies
    'konie': {},                      # Koń nie może być wymieniony w górę
    'małe psy': {},                    # Pieski nie mogą być wymienione
    'duże psy': {}
}



SORTOWANIE_ZWIERZAT = ['króliki', 'owce', 'świnie', 'krowy', 'konie', 'małe psy', 'duże psy']


# Kostki
KOSTKA_ZIELONA = ['króliki', 'króliki', 'króliki', 'króliki', 'króliki', 'króliki', 'świnie', 'owce', 'owce', 'owce', 'wilk', 'krowa']
KOSTKA_CZERWONA = ['króliki', 'króliki', 'króliki', 'króliki', 'króliki', 'króliki', 'świnie', 'świnie', 'owce', 'owce', 'koń', 'lis']

# Funkcja inicjalizująca grę
def init_game(mode="ai"):
    session['stado_glowne'] = STADO_GLOWNE.copy()
    session['gracz1'] = {'króliki': 1, 'owce': 0, 'świnie': 0, 'krowy': 0, 'konie': 0, 'małe psy': 0, 'duże psy': 0}
    session['gracz2'] = {'króliki': 1, 'owce': 0, 'świnie': 0, 'krowy': 0, 'konie': 0, 'małe psy': 0, 'duże psy': 0}
    session['aktualny_gracz'] = 1
    session['ostatni_rzut'] = None
    session['game_mode'] = mode 

# Funkcja do rzutu kostkami
def rzuc_kostkami():
    wynik_zielona = random.choice(KOSTKA_ZIELONA)
    wynik_czerwona = random.choice(KOSTKA_CZERWONA)
    return wynik_zielona, wynik_czerwona

def ai_turn():
    if session['game_mode'] == "ai" and session['aktualny_gracz'] == 2:
        # AI makes an optimal exchange
        mozliwe_wymiany = generuj_opcje_wymian(2)
        if mozliwe_wymiany:
            best_trade = mozliwe_wymiany[0]  # AI selects the first available trade
            wymiana(2, best_trade[0], best_trade[1])

        # AI rolls the dice
        wynik_zielona, wynik_czerwona = rzuc_kostkami()
        wykonaj_ruch(2, wynik_zielona, wynik_czerwona)
        session['ostatni_rzut'] = (wynik_zielona, wynik_czerwona)

        # Check for victory
        if sprawdz_wygrana(2):
            session['wygrana'] = 2
        else:
            session['aktualny_gracz'] = 1  # Return turn to player


def wykonaj_ruch(gracz, wynik_zielona, wynik_czerwona):
    stado = session[f'gracz{gracz}']
    stado_glowne = session['stado_glowne']

    # Obsługa lisa 🦊 - zabiera wszystkie króliki, jeśli gracz nie ma małego psa
    if 'lis' in [wynik_zielona, wynik_czerwona]:
        if stado.get('małe psy', 0) > 0:
            stado['małe psy'] -= 1
            stado_glowne['małe psy'] += 1  # Mały pies wraca do stada głównego
        else:
            if stado.get('króliki', 0) > 0:
                stado_glowne['króliki'] += stado['króliki']
                stado['króliki'] = 0  # Wszystkie króliki wracają do stada

    # Obsługa wilka 🐺 - zabiera wszystkie zwierzęta oprócz konia i małego psa
    if 'wilk' in [wynik_zielona, wynik_czerwona]:
        if stado.get('duże psy', 0) > 0:
            stado['duże psy'] -= 1
            stado_glowne['duże psy'] += 1  # Duży pies wraca do stada głównego
        else:
            # Lista zwierząt do stracenia (poza koniem i małym psem)
            do_straty = ['króliki', 'owce', 'świnie', 'krowy']
            for zwierze in do_straty:
                if stado.get(zwierze, 0) > 0:
                    stado_glowne[zwierze] += stado[zwierze]
                    stado[zwierze] = 0  # Utrata zwierząt

    # Jeśli gracz wyrzucił dwa identyczne zwierzęta, dostaje je (jeśli są dostępne w stadzie)
    if wynik_zielona == wynik_czerwona and wynik_zielona not in ['wilk', 'lis']:
        if stado_glowne[wynik_zielona] > 0:
            stado[wynik_zielona] += 1
            stado_glowne[wynik_zielona] -= 1

    # Dodawanie zwierząt za pełne pary (pomijając wilka i lisa)
    for wynik in [wynik_zielona, wynik_czerwona]:
        if wynik in stado and wynik not in ['wilk', 'lis']:
            liczba_par = (stado[wynik] + 1) // 2
            dostępne_w_stadzie = stado_glowne.get(wynik, 0)
            dodane_zwierzęta = min(liczba_par, dostępne_w_stadzie)
            stado[wynik] += dodane_zwierzęta
            stado_glowne[wynik] -= dodane_zwierzęta

    # Zapisanie zmian w sesji
    session[f'gracz{gracz}'] = stado
    session['stado_glowne'] = stado_glowne


def wymiana(gracz, z, na):
    """Obsługuje wymianę między graczem a głównym stadem."""
    stado = session[f'gracz{gracz}']
    stado_glowne = session['stado_glowne']

    # Jeśli to standardowa wymiana (np. 6 królików → 1 owca)
    if z in TABELA_WYMIAN and na in TABELA_WYMIAN[z]:
        wymagane_zasoby = TABELA_WYMIAN[z][na]
        if stado.get(z, 0) >= wymagane_zasoby and stado_glowne.get(na, 0) > 0:
            stado[z] -= wymagane_zasoby
            stado[na] += 1
            stado_glowne[z] += wymagane_zasoby
            stado_glowne[na] -= 1
            session[f'gracz{gracz}'] = stado
            session['stado_glowne'] = stado_glowne
            return

    # Jeśli to odwrócona wymiana (np. 1 owca → 6 królików)
    for dawca, przeliczniki in TABELA_WYMIAN.items():
        for odbiorca, ilosc in przeliczniki.items():
            if z == odbiorca and na == dawca:  # Sprawdzenie odwrotnej wymiany
                if stado.get(z, 0) >= 1 and stado_glowne.get(na, 0) >= ilosc:
                    stado[z] -= 1
                    stado[na] += ilosc
                    stado_glowne[z] += 1
                    stado_glowne[na] -= ilosc
                    session[f'gracz{gracz}'] = stado
                    session['stado_glowne'] = stado_glowne
                    return


def generuj_opcje_wymian(gracz):
    """Generuje poprawne opcje wymiany, które może wykonać gracz."""
    stado = session[f'gracz{gracz}']
    stado_glowne = session['stado_glowne']
    opcje = []

    for dawca, przeliczniki in TABELA_WYMIAN.items():
        for odbiorca, ilosc in przeliczniki.items():
            # Standardowa wymiana (np. 6 królików → 1 owca)
            if stado.get(dawca, 0) >= ilosc and stado_glowne.get(odbiorca, 0) > 0:
                opcje.append((dawca, odbiorca, ilosc, 1))  # 6 królików → 1 owca

            # Odwrotna wymiana (np. 1 owca → 6 królików)
            if stado.get(odbiorca, 0) >= 1 and stado_glowne.get(dawca, 0) >= ilosc:
                opcje.append((odbiorca, dawca, 1, ilosc))  # 1 owca → 6 królików

    return opcje

def sprawdz_wygrana(gracz):
    """Sprawdza, czy gracz wygrał (posiada przynajmniej jedno z każdego z 5 wymaganych zwierząt)."""
    stado = session[f'gracz{gracz}']
    wymagane_zwierzeta = ['króliki', 'owce', 'świnie', 'krowy', 'konie']

    for zwierze in wymagane_zwierzeta:
        if stado.get(zwierze, 0) < 1:
            return False  # Jeśli brakuje któregoś zwierzęcia, gracz jeszcze nie wygrał
    return True  # Jeśli gracz ma co najmniej po jednym z każdego zwierzęcia, wygrywa


@app.route('/', methods=['GET', 'POST'])
def index():
    if 'stado_glowne' not in session or 'restart' in request.form:
        mode = request.form.get('game_mode', 'ai')  # Default to human vs. human
        session.clear()
        init_game(mode)

    # Ustawienie domyślnych wartości
    if 'wymiana_wykonana' not in session:
        session['wymiana_wykonana'] = False
    if 'wygrana' not in session:
        session['wygrana'] = None

    if request.method == 'POST' and 'rzut' in request.form and session['wygrana'] is None:
        aktualny_gracz = session['aktualny_gracz']
        wynik_zielona, wynik_czerwona = rzuc_kostkami()
        wykonaj_ruch(aktualny_gracz, wynik_zielona, wynik_czerwona)

        session['ostatni_rzut'] = (wynik_zielona, wynik_czerwona)

        if sprawdz_wygrana(aktualny_gracz):
            session['wygrana'] = aktualny_gracz
        else:
            session['aktualny_gracz'] = 2 if aktualny_gracz == 1 else 1
            session['wymiana_wykonana'] = False

        print(session['game_mode'])
        print(session['aktualny_gracz'])
        # If AI's turn, execute its move
        if session['game_mode'] == "ai" and session['aktualny_gracz'] == 2:
            ai_turn()


    elif request.method == 'POST' and 'wymiana' in request.form and not session['wymiana_wykonana'] and session['wygrana'] is None:
        wymiana_opcja = request.form['wymiana']
        if '-' in wymiana_opcja:
            z, na = wymiana_opcja.split('-')
            aktualny_gracz = session['aktualny_gracz']
            wymiana(aktualny_gracz, z, na)
            session['wymiana_wykonana'] = True

    return render_template(
        'index.html',
        stado_glowne=session['stado_glowne'],
        gracz1=session['gracz1'],
        gracz2=session['gracz2'],
        aktualny_gracz=session['aktualny_gracz'],
        ostatni_rzut=session.get('ostatni_rzut'),
        wymiana_wykonana=session['wymiana_wykonana'],
        mozliwe_wymiany=generuj_opcje_wymian(session['aktualny_gracz']),
        wygrana=session['wygrana'],
       
    )

@app.route('/restart')
def restart():
    init_game()
    return "Gra została zrestartowana! Odśwież stronę, aby zobaczyć zmiany."

if __name__ == '__main__':
    app.run(debug=True)