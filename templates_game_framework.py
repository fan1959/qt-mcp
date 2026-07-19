"""Templates for the 'game_framework' scaffold variant.

This module is imported by server.py and exposes string-returning functions
that emit one C++ source file each. All Qt types referenced (QObject,
QString, QVector, etc.) must be #included by the emitter.

The framework implements a classic Model/View split:

    GameState   <- concrete subclass owns game-specific state (cards, board, etc.)
    GameAction  <- concrete subclass carries a player move
    GameController <- generic engine: turn order, AI dispatch, TODO rules
    AIPlayer    <- pluggable opponent brain

To wire up a specific board/card game the student fills in 3 TODO virtuals
on a GameController subclass:

    bool isValidAction(const GameState&, int playerIdx, const GameAction&) const;
    void applyAction(GameState&, int playerIdx, const GameAction&) const;
    GameResult evaluateResult(const GameState&) const;

Two reference games (HigherOrLower, GuessNumber) are included as worked
examples — read them to see how the 3 TODOs look when filled in.
"""

# All template strings are plain Python strings (raw where needed) so that
# C++ braces inside do not collide with f-string syntax.


# ---------------------------------------------------------------------------
# game/gamestate.h
# ---------------------------------------------------------------------------
def gamestate_h() -> str:
    return r"""#ifndef GAMESTATE_H
#define GAMESTATE_H

#include <QJsonObject>

// Pure-virtual base for any game's complete state snapshot.
// Subclasses serialize / restore themselves so the controller can save & replay.
class GameState {
public:
    virtual ~GameState() = default;

    // Round number (1 = first round). Incremented when a full turn cycle ends.
    virtual int roundNumber() const = 0;
    virtual void setRoundNumber(int r) = 0;

    // Index of the player whose turn it is.
    virtual int currentPlayer() const = 0;
    virtual void setCurrentPlayer(int idx) = 0;

    // Whether the game has finished; default false until evaluateResult says so.
    virtual bool isTerminal() const = 0;
    virtual void setTerminal(bool t) = 0;

    // JSON (de)serialization so games can be saved/loaded or sent over the wire.
    virtual QJsonObject toJson() const = 0;
    virtual void fromJson(const QJsonObject& obj) = 0;

    // Equality is needed by some AI strategies (transposition tables).
    virtual bool operator==(const GameState& other) const = 0;
    bool operator!=(const GameState& other) const { return !(*this == other); }
};

#endif // GAMESTATE_H
"""


# ---------------------------------------------------------------------------
# game/gameaction.h
# ---------------------------------------------------------------------------
def gameaction_h() -> str:
    return r"""#ifndef GAMEACTION_H
#define GAMEACTION_H

#include <QJsonObject>
#include <QString>

// Base class for any move a player can make.
// A subclass carries the move payload (which card, which square, what guess, ...).
// Note: virtuals have default impls (not pure-virtual) so that
// QVector<GameAction> can be instantiated — useful for action logs and AI
// enumerations. Concrete subclasses still override label/toJson/fromJson.
class GameAction {
public:
    virtual ~GameAction() = default;

    virtual QJsonObject toJson() const { return {}; }
    virtual void fromJson(const QJsonObject& /*obj*/) {}

    // A short label for the action log ("play 7 of Hearts", "guess 42", ...).
    virtual QString label() const { return QStringLiteral("?"); }
};

#endif // GAMEACTION_H
"""


# ---------------------------------------------------------------------------
# game/player.h
# ---------------------------------------------------------------------------
def player_h() -> str:
    return r"""#ifndef PLAYER_H
#define PLAYER_H

#include <QString>

class Player {
public:
    Player() = default;
    explicit Player(QString name, bool isAI = false)
        : m_name(std::move(name)), m_isAI(isAI) {}

    const QString& name() const { return m_name; }
    void setName(const QString& n) { m_name = n; }

    bool isAI() const { return m_isAI; }
    void setAI(bool ai) { m_isAI = ai; }

    int score() const { return m_score; }
    void addScore(int delta) { m_score += delta; }
    void resetScore() { m_score = 0; }

private:
    QString m_name;
    bool    m_isAI = false;
    int     m_score = 0;
};

#endif // PLAYER_H
"""


# ---------------------------------------------------------------------------
# game/aiplayer.h
# ---------------------------------------------------------------------------
def aiplayer_h() -> str:
    return r"""#ifndef AIPLAYER_H
#define AIPLAYER_H

#include <QObject>
#include "gameaction.h"
#include "gamestate.h"

class GameController;

// AIPlayer is a stateless decision maker. Subclass it to add smarter strategies
// (minimax, MCTS, heuristics...). The default RandomAI picks any valid action.
class AIPlayer : public QObject {
    Q_OBJECT
public:
    explicit AIPlayer(QObject* parent = nullptr) : QObject(parent) {}

    // Return the action this AI wants to play. Must be a valid action
    // according to GameController::isValidAction for the given player index.
    virtual GameAction decide(const GameState& state,
                              const GameController& controller,
                              int playerIdx) const = 0;

    virtual QString strategyName() const = 0;
};

// Concrete default: pick uniformly from currently-valid actions.
// To use: AIPlayer* ai = new RandomAI(this); ai->decide(state, ctrl, idx);
class RandomAI : public AIPlayer {
public:
    explicit RandomAI(QObject* parent = nullptr) : AIPlayer(parent) {}

    GameAction decide(const GameState& state,
                      const GameController& controller,
                      int playerIdx) const override;

    QString strategyName() const override { return QStringLiteral("Random"); }
};

#endif // AIPLAYER_H
"""


# ---------------------------------------------------------------------------
# game/aiplayer.cpp
# ---------------------------------------------------------------------------
def aiplayer_cpp() -> str:
    return r"""#include "aiplayer.h"
#include "gamecontroller.h"

#include <QRandomGenerator>
#include <QVector>

// NOTE: This is a stub. The default RandomAI needs a way to enumerate all
// legal actions for the current game. That requires game-specific knowledge,
// so we expose it as a virtual on GameController:

//   virtual QVector<GameAction> enumerateLegalActions(
//       const GameState& state, int playerIdx) const = 0;
//
// If a subclass doesn't implement it, RandomAI returns an empty action
// and logs a warning. Subclasses are expected to override enumerateLegalActions.

GameAction RandomAI::decide(const GameState& state,
                            const GameController& controller,
                            int playerIdx) const {
    QVector<GameAction> legal = controller.enumerateLegalActions(state, playerIdx);
    if (legal.isEmpty()) {
        qWarning("RandomAI: no legal actions enumerated for player %d. "
                 "Override GameController::enumerateLegalActions() to enable RandomAI.",
                 playerIdx);
        return GameAction();   // Empty action — game should treat as pass.
    }
    int idx = QRandomGenerator::global()->bounded(legal.size());
    return legal[idx];
}
"""


# ---------------------------------------------------------------------------
# game/gamecontroller.h
# ---------------------------------------------------------------------------
def gamecontroller_h() -> str:
    return r"""#ifndef GAMECONTROLLER_H
#define GAMECONTROLLER_H

#include <QObject>
#include <QString>
#include <QVector>
#include <memory>

#include "aiplayer.h"
#include "gameaction.h"
#include "gamestate.h"
#include "player.h"

// Result of evaluating the game state.
// winnerIndex == -1  -> game not over yet.
// winnerIndex == -2  -> draw / tie.
// winnerIndex >= 0   -> that player's index wins.
struct GameResult {
    int winnerIndex = -1;       // -1 = ongoing, -2 = draw, >=0 = winner
    QString reason;             // human-readable explanation
};

class GameController : public QObject {
    Q_OBJECT

public:
    explicit GameController(QObject* parent = nullptr);
    ~GameController() override;

    // -- Player roster ----------------------------------------------------
    int playerCount() const { return m_players.size(); }
    Player& player(int idx);
    const Player& player(int idx) const;
    void addPlayer(Player p);
    void clearPlayers();

    // -- State ------------------------------------------------------------
    GameState* state() { return m_state.get(); }
    const GameState* state() const { return m_state.get(); }
    void setState(std::unique_ptr<GameState> s);   // takes ownership

    // -- AI binding -------------------------------------------------------
    void setAI(int playerIdx, AIPlayer* ai);       // takes ownership
    AIPlayer* ai(int playerIdx) const;

    // -- Lifecycle hooks (subclass fills these) --------------------------

    // TODO 1: Return true if `action` is a legal move for `playerIdx` in `state`.
    virtual bool isValidAction(const GameState& state,
                               int playerIdx,
                               const GameAction& action) const = 0;

    // TODO 2: Mutate `state` to reflect `action` taken by `playerIdx`.
    //         Also advance turn / round as appropriate.
    virtual void applyAction(GameState& state,
                             int playerIdx,
                             const GameAction& action) = 0;

    // TODO 3: Inspect `state` and return a GameResult.
    //         Default returns {-1, ""} meaning "game not over".
    //         Override to declare win/loss/draw conditions.
    virtual GameResult evaluateResult(const GameState& state) const;

    // OPTIONAL: Enumerate every legal action for a player. RandomAI needs this.
    //           Default returns {} — RandomAI logs a warning when used.
    virtual QVector<GameAction> enumerateLegalActions(const GameState& state,
                                                      int playerIdx) const;

    // -- Built-in turn management (works for any subclass) ---------------

    // Reset state to the subclass's initial state and set player 0 to move.
    virtual void startNewGame();

    // Called by the View when a human player makes a move.
    // Rejects illegal moves silently (returns false).
    bool humanAction(int playerIdx, const GameAction& action);

    // Run a single AI tick (call from a QTimer in the View for visual pacing).
    void aiTick();

    int currentPlayerIndex() const;
    int roundNumber() const;

signals:
    void stateChanged();
    void gameOver(int winnerIdx, const QString& reason);
    void messagePosted(const QString& msg);

protected:
    void emitMessage(const QString& msg) { emit messagePosted(msg); }

private:
    QVector<Player>                         m_players;
    QVector<AIPlayer*>                      m_ais;        // null if human
    std::unique_ptr<GameState>              m_state;
};

#endif // GAMECONTROLLER_H
"""


# ---------------------------------------------------------------------------
# game/gamecontroller.cpp
# ---------------------------------------------------------------------------
def gamecontroller_cpp() -> str:
    return r"""#include "gamecontroller.h"

#include <memory>
#include <utility>

GameController::GameController(QObject* parent) : QObject(parent) {}

GameController::~GameController() {
    qDeleteAll(m_ais);
}

Player& GameController::player(int idx) { return m_players[idx]; }
const Player& GameController::player(int idx) const { return m_players[idx]; }

void GameController::addPlayer(Player p) {
    m_players.append(std::move(p));
    m_ais.append(nullptr);   // default to human
}

void GameController::clearPlayers() {
    qDeleteAll(m_ais);
    m_ais.clear();
    m_players.clear();
}

void GameController::setState(std::unique_ptr<GameState> s) {
    m_state = std::move(s);
    emit stateChanged();
}

void GameController::setAI(int playerIdx, AIPlayer* ai) {
    if (playerIdx < 0 || playerIdx >= m_ais.size()) return;
    if (m_ais[playerIdx]) delete m_ais[playerIdx];
    m_ais[playerIdx] = ai;
}

AIPlayer* GameController::ai(int playerIdx) const {
    if (playerIdx < 0 || playerIdx >= m_ais.size()) return nullptr;
    return m_ais[playerIdx];
}

GameResult GameController::evaluateResult(const GameState& /*state*/) const {
    // Default: no win condition declared. Subclass overrides this.
    return {-1, QString()};
}

QVector<GameAction> GameController::enumerateLegalActions(
        const GameState& /*state*/, int /*playerIdx*/) const {
    return {};
}

void GameController::startNewGame() {
    if (!m_state) return;
    m_state->setRoundNumber(1);
    m_state->setCurrentPlayer(0);
    m_state->setTerminal(false);
    for (Player& p : m_players) p.resetScore();
    emit stateChanged();
    emit messagePosted(QStringLiteral("New game started."));
}

bool GameController::humanAction(int playerIdx, const GameAction& action) {
    if (!m_state || m_state->isTerminal()) return false;
    if (playerIdx != m_state->currentPlayer()) {
        emit messagePosted(QStringLiteral("Not your turn."));
        return false;
    }
    if (m_players.value(playerIdx).isAI()) {
        emit messagePosted(QStringLiteral("That seat is an AI."));
        return false;
    }
    if (!isValidAction(*m_state, playerIdx, action)) {
        emit messagePosted(QStringLiteral("Illegal move."));
        return false;
    }

    applyAction(*m_state, playerIdx, action);

    // Check win
    GameResult r = evaluateResult(*m_state);
    if (r.winnerIndex != -1) {
        m_state->setTerminal(true);
        if (r.winnerIndex >= 0 && r.winnerIndex < m_players.size()) {
            m_players[r.winnerIndex].addScore(1);
        }
        emit stateChanged();
        emit gameOver(r.winnerIndex, r.reason);
        emit messagePosted(r.reason.isEmpty() ? QStringLiteral("Game over.")
                                              : r.reason);
        return true;
    }

    // Advance turn
    int next = (m_state->currentPlayer() + 1) % m_players.size();
    if (next == 0) {
        m_state->setRoundNumber(m_state->roundNumber() + 1);
    }
    m_state->setCurrentPlayer(next);

    emit stateChanged();
    return true;
}

void GameController::aiTick() {
    if (!m_state || m_state->isTerminal()) return;
    int idx = m_state->currentPlayer();
    AIPlayer* brain = ai(idx);
    if (!brain || !m_players.value(idx).isAI()) return;

    GameAction a = brain->decide(*m_state, *this, idx);
    emit messagePosted(QStringLiteral("[%1] %2 plays: %3")
        .arg(m_players[idx].name(), brain->strategyName(), a.label()));
    humanAction(idx, a);
}

int GameController::currentPlayerIndex() const {
    return m_state ? m_state->currentPlayer() : -1;
}

int GameController::roundNumber() const {
    return m_state ? m_state->roundNumber() : 0;
}
"""


# ---------------------------------------------------------------------------
# game/games/higherlower.h -- Sample game #1: Higher or Lower
# ---------------------------------------------------------------------------
def higherlower_h() -> str:
    return r"""#ifndef HIGHERLOWER_GAME_H
#define HIGHERLOWER_GAME_H

#include "../gameaction.h"
#include "../gamestate.h"
#include "../gamecontroller.h"
#include <QVector>

// ----- State -----
class HigherLowerState : public GameState {
public:
    // Visible card on the table (the one to compare against).
    int currentCard() const { return m_currentCard; }
    void setCurrentCard(int v) { m_currentCard = v; }

    // Remaining deck (face-down, shuffled). Top of deck is the front.
    QVector<int>& deck() { return m_deck; }
    const QVector<int>& deck() const { return m_deck; }
    void setDeck(QVector<int> d) { m_deck = std::move(d); }

    // Streak: how many correct guesses in a row this round.
    int streak() const { return m_streak; }
    void setStreak(int s) { m_streak = s; }

    // GameState interface
    int  roundNumber() const override { return m_round; }
    void setRoundNumber(int r) override { m_round = r; }
    int  currentPlayer() const override { return m_currentPlayer; }
    void setCurrentPlayer(int idx) override { m_currentPlayer = idx; }
    bool isTerminal() const override { return m_terminal; }
    void setTerminal(bool t) override { m_terminal = t; }

    QJsonObject toJson() const override;
    void fromJson(const QJsonObject& obj) override;

    bool operator==(const GameState& other) const override;

private:
    QVector<int> m_deck;
    int m_currentCard = 0;
    int m_streak = 0;
    int m_round = 1;
    int m_currentPlayer = 0;
    bool m_terminal = false;
};

// ----- Action -----
class HigherLowerAction : public GameAction {
public:
    enum Guess { Higher, Lower };
    Guess guess() const { return m_guess; }
    void setGuess(Guess g) { m_guess = g; }

    QString label() const override;
    QJsonObject toJson() const override;
    void fromJson(const QJsonObject& obj) override;

private:
    Guess m_guess = Higher;
};

// ----- Controller -----
class HigherLowerController : public GameController {
    Q_OBJECT
public:
    explicit HigherLowerController(QObject* parent = nullptr);

    HigherLowerState* hlState();   // convenience accessor
    const HigherLowerState* hlState() const;

    // TODO 1 — already filled in for the sample:
    bool isValidAction(const GameState& state, int playerIdx,
                       const GameAction& action) const override;

    // TODO 2 — already filled in for the sample:
    void applyAction(GameState& state, int playerIdx,
                     const GameAction& action) override;

    // TODO 3 — already filled in for the sample:
    GameResult evaluateResult(const GameState& state) const override;

    QVector<GameAction> enumerateLegalActions(const GameState& state,
                                              int playerIdx) const override;

    void startNewGame() override;

private:
    void shuffleAndDeal();
};

#endif // HIGHERLOWER_GAME_H
"""


def higherlower_cpp() -> str:
    return r"""#include "higherlower.h"

#include <QRandomGenerator>
#include <QJsonArray>
#include <algorithm>
#include <random>

QJsonObject HigherLowerState::toJson() const {
    QJsonObject o;
    QJsonArray arr;
    for (int v : m_deck) arr.append(v);
    o["deck"] = arr;
    o["currentCard"] = m_currentCard;
    o["streak"] = m_streak;
    o["round"] = m_round;
    o["currentPlayer"] = m_currentPlayer;
    o["terminal"] = m_terminal;
    return o;
}

void HigherLowerState::fromJson(const QJsonObject& obj) {
    m_deck.clear();
    for (auto v : obj["deck"].toArray()) m_deck.append(v.toInt());
    m_currentCard = obj["currentCard"].toInt();
    m_streak = obj["streak"].toInt();
    m_round = obj["round"].toInt();
    m_currentPlayer = obj["currentPlayer"].toInt();
    m_terminal = obj["terminal"].toBool();
}

bool HigherLowerState::operator==(const GameState& other) const {
    auto* o = dynamic_cast<const HigherLowerState*>(&other);
    return o && m_deck == o->m_deck
            && m_currentCard == o->m_currentCard
            && m_streak == o->m_streak
            && m_round == o->m_round
            && m_currentPlayer == o->m_currentPlayer
            && m_terminal == o->m_terminal;
}

QString HigherLowerAction::label() const {
    return m_guess == Higher ? QStringLiteral("guess higher")
                             : QStringLiteral("guess lower");
}

QJsonObject HigherLowerAction::toJson() const {
    QJsonObject o;
    o["guess"] = (m_guess == Higher ? "higher" : "lower");
    return o;
}

void HigherLowerAction::fromJson(const QJsonObject& obj) {
    m_guess = (obj["guess"].toString() == "higher") ? Higher : Lower;
}

HigherLowerController::HigherLowerController(QObject* parent)
    : GameController(parent) {
    auto s = std::make_unique<HigherLowerState>();
    setState(std::move(s));
}

HigherLowerState* HigherLowerController::hlState() {
    return static_cast<HigherLowerState*>(state());
}

const HigherLowerState* HigherLowerController::hlState() const {
    return static_cast<const HigherLowerState*>(state());
}

void HigherLowerController::shuffleAndDeal() {
    auto* s = hlState();
    QVector<int> deck = {1,2,3,4,5,6,7,8,9,10,11,12,13};
    std::random_device rd;
    std::mt19937 rng(rd());
    std::shuffle(deck.begin(), deck.end(), rng);
    s->setDeck(deck);
    s->setCurrentCard(s->deck().takeFirst());
    s->setStreak(0);
}

void HigherLowerController::startNewGame() {
    shuffleAndDeal();
    GameController::startNewGame();   // resets round/player
}

bool HigherLowerController::isValidAction(const GameState& /*state*/,
                                          int /*playerIdx*/,
                                          const GameAction& /*action*/) const {
    // Any guess is legal as long as the deck isn't empty.
    return hlState() && !hlState()->deck().isEmpty();
}

void HigherLowerController::applyAction(GameState& /*state*/,
                                        int playerIdx,
                                        const GameAction& action) {
    auto* s = hlState();
    auto* a = dynamic_cast<const HigherLowerAction*>(&action);
    if (!s || !a) return;

    int next = s->deck().first();
    bool correct = (a->guess() == HigherLowerAction::Higher)
                       ? (next > s->currentCard())
                       : (next < s->currentCard());

    QString msg = QStringLiteral("Card was %1. You guessed %2 → %3.")
        .arg(next)
        .arg(a->label(),
             correct ? QStringLiteral("correct") : QStringLiteral("wrong"));
    emit messagePosted(msg);

    if (correct) {
        s->setStreak(s->streak() + 1);
        s->setCurrentCard(next);
        s->deck().removeFirst();
    } else {
        // Score this round for the player who missed.
        player(playerIdx).addScore(s->streak());
        // Reshuffle for next round.
        shuffleAndDeal();
    }
}

GameResult HigherLowerController::evaluateResult(const GameState& state) const {
    auto* s = static_cast<const HigherLowerState*>(&state);
    if (s->roundNumber() > 5) {
        // Game ends after 5 rounds. Highest score wins.
        int best = 0;
        for (int i = 1; i < playerCount(); ++i) {
            if (player(i).score() > player(best).score()) best = i;
        }
        bool draw = false;
        for (int i = 0; i < playerCount(); ++i) {
            if (i != best && player(i).score() == player(best).score()) {
                draw = true; break;
            }
        }
        if (draw) return {-2, QStringLiteral("Draw game.")};
        return {best, QStringLiteral("Player %1 wins with %2 points.")
                       .arg(player(best).name()).arg(player(best).score())};
    }
    return {-1, QString()};
}

QVector<GameAction> HigherLowerController::enumerateLegalActions(
        const GameState& /*state*/, int /*playerIdx*/) const {
    QVector<GameAction> out;
    if (hlState() && hlState()->deck().isEmpty()) return out;
    HigherLowerAction a1; a1.setGuess(HigherLowerAction::Higher); out.append(a1);
    HigherLowerAction a2; a2.setGuess(HigherLowerAction::Lower);  out.append(a2);
    return out;
}
"""


# ---------------------------------------------------------------------------
# game/games/guessnumber.h -- Sample game #2: Guess the Number
# ---------------------------------------------------------------------------
def guessnumber_h() -> str:
    return r"""#ifndef GUESSNUMBER_GAME_H
#define GUESSNUMBER_GAME_H

#include "../gameaction.h"
#include "../gamestate.h"
#include "../gamecontroller.h"

// ----- State -----
class GuessNumberState : public GameState {
public:
    int target() const { return m_target; }
    void setTarget(int t) { m_target = t; }

    int minBound() const { return m_min; }
    void setMinBound(int m) { m_min = m; }
    int maxBound() const { return m_max; }
    void setMaxBound(int m) { m_max = m; }

    int lastGuess() const { return m_lastGuess; }
    void setLastGuess(int g) { m_lastGuess = g; }

    int attemptsLeft() const { return m_attemptsLeft; }
    void setAttemptsLeft(int a) { m_attemptsLeft = a; }

    int  roundNumber() const override { return m_round; }
    void setRoundNumber(int r) override { m_round = r; }
    int  currentPlayer() const override { return m_currentPlayer; }
    void setCurrentPlayer(int idx) override { m_currentPlayer = idx; }
    bool isTerminal() const override { return m_terminal; }
    void setTerminal(bool t) override { m_terminal = t; }

    QJsonObject toJson() const override;
    void fromJson(const QJsonObject& obj) override;
    bool operator==(const GameState& other) const override;

private:
    int m_target = 0;
    int m_min = 1;
    int m_max = 100;
    int m_lastGuess = 0;
    int m_attemptsLeft = 7;
    int m_round = 1;
    int m_currentPlayer = 0;
    bool m_terminal = false;
};

// ----- Action -----
class GuessNumberAction : public GameAction {
public:
    int guess() const { return m_guess; }
    void setGuess(int g) { m_guess = g; }
    QString label() const override { return QStringLiteral("guess %1").arg(m_guess); }
    QJsonObject toJson() const override;
    void fromJson(const QJsonObject& obj) override;
private:
    int m_guess = 0;
};

// ----- Controller -----
class GuessNumberController : public GameController {
    Q_OBJECT
public:
    explicit GuessNumberController(QObject* parent = nullptr);

    GuessNumberState* gnState();
    const GuessNumberState* gnState() const;

    bool isValidAction(const GameState& state, int playerIdx,
                       const GameAction& action) const override;
    void applyAction(GameState& state, int playerIdx,
                     const GameAction& action) override;
    GameResult evaluateResult(const GameState& state) const override;
    QVector<GameAction> enumerateLegalActions(const GameState& state,
                                              int playerIdx) const override;

    void startNewGame() override;
};

#endif // GUESSNUMBER_GAME_H
"""


def guessnumber_cpp() -> str:
    return r"""#include "guessnumber.h"

#include <QRandomGenerator>
#include <QJsonArray>

QJsonObject GuessNumberState::toJson() const {
    QJsonObject o;
    o["target"] = m_target;
    o["min"] = m_min;
    o["max"] = m_max;
    o["lastGuess"] = m_lastGuess;
    o["attemptsLeft"] = m_attemptsLeft;
    o["round"] = m_round;
    o["currentPlayer"] = m_currentPlayer;
    o["terminal"] = m_terminal;
    return o;
}

void GuessNumberState::fromJson(const QJsonObject& obj) {
    m_target = obj["target"].toInt();
    m_min = obj["min"].toInt();
    m_max = obj["max"].toInt();
    m_lastGuess = obj["lastGuess"].toInt();
    m_attemptsLeft = obj["attemptsLeft"].toInt();
    m_round = obj["round"].toInt();
    m_currentPlayer = obj["currentPlayer"].toInt();
    m_terminal = obj["terminal"].toBool();
}

bool GuessNumberState::operator==(const GameState& other) const {
    auto* o = dynamic_cast<const GuessNumberState*>(&other);
    return o && m_target == o->m_target && m_min == o->m_min
            && m_max == o->m_max && m_lastGuess == o->m_lastGuess
            && m_attemptsLeft == o->m_attemptsLeft && m_round == o->m_round
            && m_currentPlayer == o->m_currentPlayer && m_terminal == o->m_terminal;
}

QJsonObject GuessNumberAction::toJson() const {
    QJsonObject o; o["guess"] = m_guess; return o;
}
void GuessNumberAction::fromJson(const QJsonObject& obj) { m_guess = obj["guess"].toInt(); }

GuessNumberController::GuessNumberController(QObject* parent)
    : GameController(parent) {
    auto s = std::make_unique<GuessNumberState>();
    setState(std::move(s));
}

GuessNumberState* GuessNumberController::gnState() {
    return static_cast<GuessNumberState*>(state());
}

const GuessNumberState* GuessNumberController::gnState() const {
    return static_cast<const GuessNumberState*>(state());
}

void GuessNumberController::startNewGame() {
    auto* s = gnState();
    s->setTarget(QRandomGenerator::global()->bounded(s->minBound(), s->maxBound() + 1));
    s->setLastGuess(0);
    s->setAttemptsLeft(7);
    GameController::startNewGame();
    emit messagePosted(QStringLiteral("I'm thinking of a number between %1 and %2.")
        .arg(s->minBound()).arg(s->maxBound()));
}

bool GuessNumberController::isValidAction(const GameState& state,
                                          int /*playerIdx*/,
                                          const GameAction& action) const {
    auto* a = dynamic_cast<const GuessNumberAction*>(&action);
    auto* s = static_cast<const GuessNumberState*>(&state);
    return a && s && a->guess() >= s->minBound() && a->guess() <= s->maxBound();
}

void GuessNumberController::applyAction(GameState& state, int playerIdx,
                                        const GameAction& action) {
    auto* s = static_cast<GuessNumberState*>(&state);
    auto* a = dynamic_cast<const GuessNumberAction*>(&action);
    if (!s || !a) return;

    s->setLastGuess(a->guess());
    s->setAttemptsLeft(s->attemptsLeft() - 1);

    if (a->guess() == s->target()) {
        player(playerIdx).addScore(s->attemptsLeft() + 1);   // more attempts left = more points
        emit messagePosted(QStringLiteral("Correct! %1 it is.").arg(s->target()));
    } else if (a->guess() < s->target()) {
        emit messagePosted(QStringLiteral("Higher than %1.").arg(a->guess()));
    } else {
        emit messagePosted(QStringLiteral("Lower than %1.").arg(a->guess()));
    }
}

GameResult GuessNumberController::evaluateResult(const GameState& state) const {
    auto* s = static_cast<const GuessNumberState*>(&state);
    if (s->lastGuess() == s->target()) {
        // Find the player who just guessed correctly.
        return {s->currentPlayer(),
                QStringLiteral("Player %1 found the number!").arg(player(s->currentPlayer()).name())};
    }
    if (s->attemptsLeft() <= 0) {
        // Out of attempts — the player whose turn it is loses.
        int loser = s->currentPlayer();
        int best = (loser == 0) ? 1 : 0;
        for (int i = 0; i < playerCount(); ++i) {
            if (i != loser && player(i).score() >= player(best).score()) best = i;
        }
        return {best, QStringLiteral("Out of guesses. %1 wins.")
                       .arg(player(best).name())};
    }
    if (s->roundNumber() > 3) {
        int best = 0;
        for (int i = 1; i < playerCount(); ++i) {
            if (player(i).score() > player(best).score()) best = i;
        }
        return {best, QStringLiteral("Game over. %1 wins.")
                       .arg(player(best).name())};
    }
    return {-1, QString()};
}

QVector<GameAction> GuessNumberController::enumerateLegalActions(
        const GameState& /*state*/, int /*playerIdx*/) const {
    // Continuous range — don't enumerate; RandomAI is useless here.
    return {};
}
"""


# ===========================================================================
# View templates for the game_framework scaffold.
# ===========================================================================


def gridwidget_h() -> str:
    return r"""#ifndef GRIDWIDGET_H
#define GRIDWIDGET_H

#include <QWidget>
#include <QVector>

class GridWidget : public QWidget {
    Q_OBJECT
    Q_PROPERTY(int rows READ rows WRITE setRows NOTIFY gridChanged)
    Q_PROPERTY(int cols READ cols WRITE setCols NOTIFY gridChanged)

public:
    explicit GridWidget(QWidget* parent = nullptr);

    int rows() const { return m_rows; }
    int cols() const { return m_cols; }
    void setRows(int r);
    void setCols(int c);
    void setGrid(int r, int c);

    // Each cell is a free-form string ("A1", "♠7", "X", " 5 ").
    void setCell(int r, int c, const QString& text);
    QString cell(int r, int c) const;

    // Background color of an individual cell (default = light gray).
    void setCellColor(int r, int c, const QColor& color);
    void clearCellColors();

    QSize sizeHint() const override { return QSize(600, 400); }

signals:
    void gridChanged();
    void cellClicked(int r, int c);

protected:
    void paintEvent(QPaintEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;

private:
    int m_rows = 8;
    int m_cols = 8;
    QVector<QString> m_cells;
    QVector<QColor>  m_colors;
    QRect cellRect(int r, int c) const;
};

#endif // GRIDWIDGET_H
"""


def gridwidget_cpp() -> str:
    return r"""#include "gridwidget.h"

#include <QPainter>
#include <QPaintEvent>
#include <QMouseEvent>

GridWidget::GridWidget(QWidget* parent) : QWidget(parent) {
    setGrid(m_rows, m_cols);
}

void GridWidget::setRows(int r) { setGrid(r, m_cols); }
void GridWidget::setCols(int c) { setGrid(m_rows, c); }

void GridWidget::setGrid(int r, int c) {
    m_rows = qMax(1, r);
    m_cols = qMax(1, c);
    m_cells.fill(QString(), m_rows * m_cols);
    m_colors.fill(QColor(Qt::lightGray), m_rows * m_cols);
    update();
    emit gridChanged();
}

void GridWidget::setCell(int r, int c, const QString& text) {
    if (r < 0 || c < 0 || r >= m_rows || c >= m_cols) return;
    m_cells[r * m_cols + c] = text;
    update();
}

QString GridWidget::cell(int r, int c) const {
    if (r < 0 || c < 0 || r >= m_rows || c >= m_cols) return {};
    return m_cells[r * m_cols + c];
}

void GridWidget::setCellColor(int r, int c, const QColor& color) {
    if (r < 0 || c < 0 || r >= m_rows || c >= m_cols) return;
    m_colors[r * m_cols + c] = color;
    update();
}

void GridWidget::clearCellColors() {
    m_colors.fill(QColor(Qt::lightGray), m_rows * m_cols);
    update();
}

QRect GridWidget::cellRect(int r, int c) const {
    const int W = width(), H = height();
    const int cw = W / m_cols, ch = H / m_rows;
    return QRect(c * cw, r * ch, cw, ch);
}

void GridWidget::paintEvent(QPaintEvent* /*event*/) {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing, false);

    const int W = width(), H = height();
    const int cw = W / m_cols, ch = H / m_rows;

    // Background
    p.fillRect(rect(), QColor(245, 245, 245));

    // Cells
    p.setPen(QPen(Qt::darkGray, 1));
    for (int r = 0; r < m_rows; ++r) {
        for (int c = 0; c < m_cols; ++c) {
            QRect rc(c * cw, r * ch, cw, ch);
            p.fillRect(rc, m_colors.value(r * m_cols + c, QColor(Qt::lightGray)));
            p.drawRect(rc);

            const QString& txt = m_cells.value(r * m_cols + c);
            if (!txt.isEmpty()) {
                p.setPen(Qt::black);
                p.drawText(rc, Qt::AlignCenter, txt);
            }
        }
    }
}

void GridWidget::mousePressEvent(QMouseEvent* event) {
    int cw = width() / m_cols;
    int ch = height() / m_rows;
    if (cw <= 0 || ch <= 0) return;
    int c = event->pos().x() / cw;
    int r = event->pos().y() / ch;
    if (r >= 0 && r < m_rows && c >= 0 && c < m_cols) {
        emit cellClicked(r, c);
    }
}
"""


def cardwidget_h() -> str:
    return r"""#ifndef CARDWIDGET_H
#define CARDWIDGET_H

#include <QWidget>

class CardWidget : public QWidget {
    Q_OBJECT
    Q_PROPERTY(QString face READ faceText WRITE setFaceText NOTIFY faceChanged)
    Q_PROPERTY(bool faceUp READ faceUp WRITE setFaceUp NOTIFY faceChanged)

public:
    explicit CardWidget(QWidget* parent = nullptr);

    QString faceText() const { return m_face; }
    void setFaceText(const QString& f);

    bool faceUp() const { return m_faceUp; }
    void setFaceUp(bool f);

    void setSuitColor(const QColor& c) { m_suitColor = c; update(); }

    QSize sizeHint() const override { return QSize(80, 120); }

signals:
    void faceChanged();
    void clicked();

protected:
    void paintEvent(QPaintEvent* event) override;
    void mousePressEvent(QMouseEvent* event) override;

private:
    QString m_face = "A";
    bool    m_faceUp = true;
    QColor  m_suitColor = Qt::black;
};

#endif // CARDWIDGET_H
"""


def cardwidget_cpp() -> str:
    return r"""#include "cardwidget.h"

#include <QPainter>
#include <QPaintEvent>
#include <QMouseEvent>

CardWidget::CardWidget(QWidget* parent) : QWidget(parent) {}

void CardWidget::setFaceText(const QString& f) { m_face = f; update(); emit faceChanged(); }
void CardWidget::setFaceUp(bool f)              { m_faceUp = f; update(); emit faceChanged(); }

void CardWidget::paintEvent(QPaintEvent* /*event*/) {
    QPainter p(this);
    p.setRenderHint(QPainter::Antialiasing);

    const QRectF r = rect().adjusted(2, 2, -2, -2);
    const qreal radius = 8.0;

    p.setPen(m_faceUp ? QPen(Qt::black, 1) : QPen(Qt::darkBlue, 2));
    p.setBrush(m_faceUp ? QColor(Qt::white) : QColor(60, 80, 160));
    p.drawRoundedRect(r, radius, radius);

    if (!m_faceUp) {
        p.setPen(Qt::NoPen);
        p.setBrush(QColor(80, 100, 180));
        p.drawRoundedRect(r.adjusted(8, 8, -8, -8), radius, radius);
        return;
    }

    p.setPen(m_suitColor);
    QFont f = p.font();
    f.setPointSizeF(20);
    f.setBold(true);
    p.setFont(f);
    p.drawText(r, Qt::AlignCenter, m_face);
}

void CardWidget::mousePressEvent(QMouseEvent* /*event*/) { emit clicked(); }
"""


def gameview_h() -> str:
    return r"""#ifndef GAMEVIEW_H
#define GAMEVIEW_H

#include <QWidget>
#include <QList>
#include <QVBoxLayout>

class GameController;
class GridWidget;
class CardWidget;

// GameView is the main playing-field widget. It hosts a GridWidget for
// board games, a hand of CardWidgets for card games, or both. Subclass it
// (or write a new one) when you need a more game-specific layout.
class GameView : public QWidget {
    Q_OBJECT
public:
    explicit GameView(QWidget* parent = nullptr);
    ~GameView() override;

    void setController(GameController* ctrl);

    GridWidget* grid() { return m_grid; }
    CardWidget* cardSlot(int idx);

protected:
    void showEvent(QShowEvent* event) override;

private slots:
    void onStateChanged();
    void onGameOver(int winnerIdx, const QString& reason);

private:
    GameController* m_controller = nullptr;
    GridWidget*     m_grid       = nullptr;
    QList<CardWidget*> m_cards;
    QVBoxLayout*     m_layout = nullptr;
};

#endif // GAMEVIEW_H
"""


def gameview_cpp() -> str:
    return r"""#include "gameview.h"
#include "../game/gamecontroller.h"
#include "../game/player.h"
#include "gridwidget.h"
#include "cardwidget.h"

#include <QHBoxLayout>
#include <QLabel>
#include <QVBoxLayout>

GameView::GameView(QWidget* parent) : QWidget(parent) {
    m_layout = new QVBoxLayout(this);
    m_layout->setContentsMargins(8, 8, 8, 8);

    // Default: an 8x8 grid (placeholder for board games).
    m_grid = new GridWidget(this);
    m_grid->setGrid(8, 8);
    m_layout->addWidget(m_grid, /*stretch*/ 1);

    // Reserve a row of card slots at the bottom (placeholder for card games).
    QHBoxLayout* cardRow = new QHBoxLayout;
    cardRow->addStretch();
    for (int i = 0; i < 5; ++i) {
        CardWidget* c = new CardWidget(this);
        c->setVisible(false);
        m_cards.append(c);
        cardRow->addWidget(c);
    }
    cardRow->addStretch();
    m_layout->addLayout(cardRow);
}

GameView::~GameView() {
    if (m_controller) m_controller->disconnect(this);
}

void GameView::setController(GameController* ctrl) {
    m_controller = ctrl;
    if (!m_controller) return;
    connect(m_controller, &GameController::stateChanged,
            this, &GameView::onStateChanged);
    connect(m_controller, &GameController::gameOver,
            this, &GameView::onGameOver);
    onStateChanged();
}

CardWidget* GameView::cardSlot(int idx) {
    if (idx < 0 || idx >= m_cards.size()) return nullptr;
    return m_cards[idx];
}

void GameView::showEvent(QShowEvent* event) {
    QWidget::showEvent(event);
    onStateChanged();
}

void GameView::onStateChanged() {
    if (!m_controller) return;

    // Show one face-up card for card games (placeholder for the "current" card).
    // Subclasses can override this to drive the actual game UI.
    auto* s = m_controller->state();
    if (!s) return;

    // Demo: highlight cell (0, currentPlayer) on the grid as a turn indicator.
    m_grid->clearCellColors();
    int cp = m_controller->currentPlayerIndex();
    if (cp >= 0) {
        m_grid->setCellColor(0, cp % m_grid->cols(), QColor(180, 220, 255));
        m_grid->setCell(0, cp % m_grid->cols(),
                        QStringLiteral("P%1").arg(cp + 1));
    }
    m_grid->setCell(2, 2, QStringLiteral("Round %1").arg(m_controller->roundNumber()));

    // TODO: replace this with game-specific rendering driven by the concrete
    //       GameState subclass. For example, for HigherOrLower:
    //         cardSlot(0)->setFaceText(QString::number(hlState()->currentCard()));
    //         cardSlot(0)->setVisible(true);
    //       For a chess-like board:
    //         populate the grid from a 2D board representation.
}

void GameView::onGameOver(int winnerIdx, const QString& reason) {
    // Color the top row green for the winner (very simple feedback).
    m_grid->clearCellColors();
    if (winnerIdx >= 0) {
        for (int c = 0; c < m_grid->cols(); ++c) {
            m_grid->setCellColor(0, c, QColor(180, 255, 180));
        }
    }
    Q_UNUSED(reason);
}
"""


def mainwindow_h() -> str:
    return r"""#ifndef MYGAMEWINDOW_H
#define MYGAMEWINDOW_H

#include <QMainWindow>

QT_BEGIN_NAMESPACE
namespace Ui { class MyGameWindow; }
QT_END_NAMESPACE

class GameController;
class GameView;

class MyGameWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MyGameWindow(QWidget* parent = nullptr);
    ~MyGameWindow() override;

    void setController(GameController* ctrl);

private slots:
    void onActionNewGame();
    void onActionQuit();
    void onActionAbout();
    void onActionSwitchGame(int index);
    void onMessagePosted(const QString& msg);
    void onGameOver(int winnerIdx, const QString& reason);
    void onHumanGuessHigher();
    void onHumanGuessLower();
    void onHumanGuessSubmit();

private:
    void setupSidebar();
    void connectController();
    void refreshSidebar();

    Ui::MyGameWindow*  ui;
    GameController*    m_controller = nullptr;
    GameView*          m_view       = nullptr;
    QStringList        m_gameChoices;
    int                m_currentGameIdx = 0;
};

#endif // MYGAMEWINDOW_H
"""


def mainwindow_cpp() -> str:
    return r"""#include "mygamewindow.h"
#include "ui_mygamewindow.h"

#include "../game/gamecontroller.h"
#include "../game/player.h"
#include "../game/games/higherlower.h"
#include "../game/games/guessnumber.h"
#include "view/gameview.h"

#include <QInputDialog>
#include <QMessageBox>
#include <QTimer>

MyGameWindow::MyGameWindow(QWidget* parent)
    : QMainWindow(parent), ui(new Ui::MyGameWindow) {
    ui->setupUi(this);
    setupSidebar();

    m_view = new GameView(this);
    ui->centralLayout->addWidget(m_view);

    // Populate game chooser.
    m_gameChoices << QStringLiteral("Higher or Lower")
                  << QStringLiteral("Guess the Number");
    ui->gameCombo->addItems(m_gameChoices);
    connect(ui->gameCombo, qOverload<int>(&QComboBox::currentIndexChanged),
            this, &MyGameWindow::onActionSwitchGame);

    // Menu / toolbar wiring.
    connect(ui->actionNewGame, &QAction::triggered, this, &MyGameWindow::onActionNewGame);
    connect(ui->actionQuit,    &QAction::triggered, this, &MyGameWindow::onActionQuit);
    connect(ui->actionAbout,   &QAction::triggered, this, &MyGameWindow::onActionAbout);

    connect(ui->btnGuessHigher, &QPushButton::clicked,
            this, &MyGameWindow::onHumanGuessHigher);
    connect(ui->btnGuessLower,  &QPushButton::clicked,
            this, &MyGameWindow::onHumanGuessLower);
    connect(ui->btnSubmitGuess, &QPushButton::clicked,
            this, &MyGameWindow::onHumanGuessSubmit);

    // Default: Higher or Lower.
    onActionSwitchGame(0);
}

MyGameWindow::~MyGameWindow() {
    delete ui;
}

void MyGameWindow::setupSidebar() {
    // Initial 2 players. Player list lives in the controller; the sidebar is a view.
    // We populate the player list panel lazily inside setController.
    ui->playerList->setHeaderLabels(QStringList{ QStringLiteral("Seat"),
                                                 QStringLiteral("Name"),
                                                 QStringLiteral("Kind"),
                                                 QStringLiteral("Score") });
}

void MyGameWindow::setController(GameController* ctrl) {
    if (m_controller == ctrl) return;
    if (m_controller) m_controller->disconnect(this);
    m_controller = ctrl;
    if (!m_controller) return;
    connectController();
    m_view->setController(m_controller);
    refreshSidebar();
}

void MyGameWindow::connectController() {
    connect(m_controller, &GameController::stateChanged,
            this, [this]{ refreshSidebar(); });
    connect(m_controller, &GameController::messagePosted,
            this, &MyGameWindow::onMessagePosted);
    connect(m_controller, &GameController::gameOver,
            this, &MyGameWindow::onGameOver);
}

void MyGameWindow::refreshSidebar() {
    if (!m_controller) return;
    ui->playerList->clear();
    int cp = m_controller->currentPlayerIndex();
    for (int i = 0; i < m_controller->playerCount(); ++i) {
        const Player& p = m_controller->player(i);
        auto* row = new QTreeWidgetItem(ui->playerList);
        row->setText(0, QString::number(i + 1));
        row->setText(1, p.name());
        row->setText(2, p.isAI() ? QStringLiteral("AI") : QStringLiteral("Human"));
        row->setText(3, QString::number(p.score()));
        if (i == cp) {
            for (int c = 0; c < 4; ++c) {
                row->setBackground(c, QColor(220, 240, 255));
            }
        }
    }
    ui->statusbar->showMessage(
        QStringLiteral("Round %1 — %2's turn")
            .arg(m_controller->roundNumber())
            .arg(m_controller->player(cp).name()));
}

void MyGameWindow::onActionNewGame() {
    if (!m_controller) return;
    m_controller->startNewGame();
    onMessagePosted(QStringLiteral("--- New game ---"));
}

void MyGameWindow::onActionQuit() { close(); }

void MyGameWindow::onActionAbout() {
    QMessageBox::about(this, tr("About"),
        tr("Qt 棋牌游戏框架\n\n"
           "这是一个可扩展的通用框架，\n"
           "等老师布置具体游戏后，在 game/games/ 下新建文件实现 3 个 TODO 函数即可。"));
}

void MyGameWindow::onActionSwitchGame(int index) {
    if (index < 0 || index >= m_gameChoices.size()) return;
    m_currentGameIdx = index;

    GameController* newCtrl = nullptr;
    if (index == 0) {
        auto* hl = new HigherLowerController(this);
        hl->addPlayer(Player(QStringLiteral("You"),    /*isAI=*/false));
        hl->addPlayer(Player(QStringLiteral("CPU"),    /*isAI=*/true));
        hl->setAI(1, new RandomAI(hl));
        newCtrl = hl;
        ui->stackedActions->setCurrentWidget(ui->pageHigherLower);
    } else {
        auto* gn = new GuessNumberController(this);
        gn->addPlayer(Player(QStringLiteral("You"), false));
        gn->setAI(0, nullptr);   // human-only for GuessNumber demo
        newCtrl = gn;
        ui->stackedActions->setCurrentWidget(ui->pageGuessNumber);
    }

    setController(newCtrl);
    onActionNewGame();
}

void MyGameWindow::onMessagePosted(const QString& msg) {
    ui->logList->addItem(msg);
    // Trim the log so it doesn't grow forever.
    while (ui->logList->count() > 200) {
        delete ui->logList->takeItem(0);
    }
    ui->logList->scrollToBottom();
}

void MyGameWindow::onGameOver(int winnerIdx, const QString& reason) {
    QString who = (winnerIdx == -2)
        ? QStringLiteral("Draw")
        : (winnerIdx >= 0 && winnerIdx < m_controller->playerCount())
              ? m_controller->player(winnerIdx).name()
              : QStringLiteral("Nobody");
    QMessageBox::information(this, tr("Game Over"),
        tr("%1\n\nWinner: %2").arg(reason, who));
}

void MyGameWindow::onHumanGuessHigher() {
    if (!m_controller) return;
    HigherLowerAction a; a.setGuess(HigherLowerAction::Higher);
    m_controller->humanAction(m_controller->currentPlayerIndex(), a);
}

void MyGameWindow::onHumanGuessLower() {
    if (!m_controller) return;
    HigherLowerAction a; a.setGuess(HigherLowerAction::Lower);
    m_controller->humanAction(m_controller->currentPlayerIndex(), a);
}

void MyGameWindow::onHumanGuessSubmit() {
    if (!m_controller) return;
    bool ok = false;
    int g = QInputDialog::getInt(this, tr("Guess"), tr("Your guess:"), 50, 1, 100, 1, &ok);
    if (!ok) return;
    GuessNumberAction a; a.setGuess(g);
    m_controller->humanAction(m_controller->currentPlayerIndex(), a);
}
"""


def mainwindow_ui() -> str:
    return r"""<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MyGameWindow</class>
 <widget class="QMainWindow" name="MyGameWindow">
  <property name="geometry"><rect><x>0</x><y>0</y><width>1000</width><height>700</height></rect></property>
  <property name="windowTitle"><string>Qt 棋牌游戏框架</string></property>

  <widget class="QWidget" name="centralwidget">
   <layout class="QHBoxLayout" name="centralLayout">

    <item>
     <widget class="QStackedWidget" name="stackedActions">
      <widget class="QWidget" name="pageHigherLower">
       <layout class="QHBoxLayout">
        <item><widget class="QPushButton" name="btnGuessHigher"><property name="text"><string>猜更大 (Higher)</string></property></widget></item>
        <item><widget class="QPushButton" name="btnGuessLower"><property name="text"><string>猜更小 (Lower)</string></property></widget></item>
       </layout>
      </widget>
      <widget class="QWidget" name="pageGuessNumber">
       <layout class="QHBoxLayout">
        <item><widget class="QPushButton" name="btnSubmitGuess"><property name="text"><string>输入我的猜测</string></property></widget></item>
       </layout>
      </widget>
     </widget>
    </item>

    <item>
     <widget class="QWidget" name="rightPane">
      <property name="maximumSize"><size><width>340</width><height>16777215</height></size></property>
      <layout class="QVBoxLayout">
       <item><widget class="QLabel"><property name="text"><string>游戏类型</string></property></widget></item>
       <item><widget class="QComboBox" name="gameCombo"/></item>
       <item><widget class="QLabel"><property name="text"><string>玩家</string></property></widget></item>
       <item><widget class="QTreeWidget" name="playerList"/></item>
       <item><widget class="QLabel"><property name="text"><string>事件日志</string></property></widget></item>
       <item><widget class="QListWidget" name="logList"/></item>
      </layout>
     </widget>
    </item>

   </layout>
  </widget>

  <widget class="QMenuBar" name="menubar">
   <property name="geometry"><rect><x>0</x><y>0</y><width>1000</width><height>22</height></rect></property>
   <widget class="QMenu" name="menuGame">
    <property name="title"><string>游戏</string></property>
    <addaction name="actionNewGame"/>
    <addaction name="separator"/>
    <addaction name="actionQuit"/>
   </widget>
   <widget class="QMenu" name="menuHelp">
    <property name="title"><string>帮助</string></property>
    <addaction name="actionAbout"/>
   </widget>
   <addaction name="menuGame"/>
   <addaction name="menuHelp"/>
  </widget>

  <widget class="QStatusBar" name="statusbar"/>

  <widget class="QToolBar" name="toolBar">
   <property name="geometry"><rect><x>0</x><y>22</y><width>1000</width><height>26</height></rect></property>
   <addaction name="actionNewGame"/>
  </widget>

  <action name="actionNewGame"><property name="text"><string>新游戏</string></property></action>
  <action name="actionQuit"><property name="text"><string>退出</string></property></action>
  <action name="actionAbout"><property name="text"><string>关于</string></property></action>

 </widget>
 <resources/>
 <connections/>
</ui>
"""


def main_cpp() -> str:
    return r"""#include <QApplication>
#include "mygamewindow.h"

int main(int argc, char* argv[]) {
    QApplication a(argc, argv);
    MyGameWindow w;
    w.show();
    return a.exec();
}
"""


def pro_file() -> str:
    return r"""QT       += core gui widgets

CONFIG   += c++17
TARGET   = mygame
TEMPLATE = app

SOURCES += \
           main.cpp \
           mygamewindow.cpp \
           game/gamecontroller.cpp \
           game/aiplayer.cpp \
           game/games/higherlower.cpp \
           game/games/guessnumber.cpp \
           view/gameview.cpp \
           view/gridwidget.cpp \
           view/cardwidget.cpp

HEADERS += \
           mygamewindow.h \
           game/gamestate.h \
           game/gameaction.h \
           game/player.h \
           game/aiplayer.h \
           game/gamecontroller.h \
           game/games/higherlower.h \
           game/games/guessnumber.h \
           view/gameview.h \
           view/gridwidget.h \
           view/cardwidget.h

FORMS   += \
           mygamewindow.ui

# Default rules for deployment.
qnx: target.path = /tmp/$${TARGET}/bin
else: target.path = $$[QT_INSTALL_BINS]/$${TARGET}
!isEmpty(target.path): INSTALLS += target
"""


def readme_md() -> str:
    return r"""# 棋牌游戏框架 (game_framework)

这是一个**通用** Qt 棋牌游戏脚手架，老师还没布置具体游戏时先用它。

## 你（学生）需要做什么

等老师布置具体游戏后，只需要：

1. 在 `game/games/` 下新建 `<your_game>.h` 和 `<your_game>.cpp`
2. 仿照 `higherlower.h/cpp` 写：
   - `<Your>State`（继承 `GameState`）
   - `<Your>Action`（继承 `GameAction`）
   - `<Your>Controller`（继承 `GameController`），实现 3 个 TODO 函数：
     - `isValidAction(state, playerIdx, action)` — 这步合不合法
     - `applyAction(state, playerIdx, action)` — 应用这步
     - `evaluateResult(state)` — 判定胜负，返回 `{-1=继续, 0..N=胜者, -2=平局}`
3. 在 `mygamewindow.cpp` 的 `onActionSwitchGame` 里加一个分支：
   ```cpp
   auto* g = new YourController(this);
   g->addPlayer(Player("You", false));
   g->addPlayer(Player("CPU", true));
   g->setAI(1, new RandomAI(g));
   newCtrl = g;
   ```
4. 如果需要新按钮，在 `mygamewindow.ui` 的 `stackedActions` 加新 page

**框架会自动接管**：回合切换、AI 调用、信号发射、UI 刷新、胜负弹窗、日志记录。

## 已有 2 个示范游戏

- **Higher or Lower**：庄家翻牌，玩家猜下一张高/低。`game/games/higherlower.cpp`
- **Guess the Number**：猜 1-100 之间的数字。`game/games/guessnumber.cpp`

读这两个文件的实现就懂 3 个 TODO 怎么写了。

## UI 部分说明

布局已写好（菜单/工具栏/侧栏/状态栏/中央 GameView），
样式（颜色/字体/动画）保留默认，等你装好 UI 设计的 skill 后再美化。
"""