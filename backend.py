from fastapi import FastAPI
from pydantic import BaseModel
import chess
import chess.engine

# Load Stockfish engine
engine = chess.engine.SimpleEngine.popen_uci("stockfish/stockfish")

app = FastAPI()
board = chess.Board()

class MoveRequest(BaseModel):
    move: str  # UCI format (e2e4, g1f3, etc.)
    skill_level: int = 10  # 0–20
    time: float = 0.5  # seconds per move

@app.post("/move")
def make_move(req: MoveRequest):
    global board
    try:
        board.push_uci(req.move)
    except:
        return {"error": "Invalid move"}

    # Configure Stockfish difficulty
    engine.configure({"Skill Level": req.skill_level})

    # Stockfish plays
    result = engine.play(board, chess.engine.Limit(time=req.time))
    board.push(result.move)

    return {
        "user_move": req.move,
        "engine_move": result.move.uci(),
        "fen": board.fen(),
        "game_over": board.is_game_over(),
        "result": board.result() if board.is_game_over() else None
    }

@app.get("/reset")
def reset_game():
    global board
    board = chess.Board()
    return {"message": "Game reset", "fen": board.fen()}
