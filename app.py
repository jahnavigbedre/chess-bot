from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import chess
import chess.engine
import chess.pgn
import os
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChessGame:
    def __init__(self):
        self.board = chess.Board()
        self.engine_path = self.find_stockfish()
        self.engine = None
        self.game_history = []
        self.difficulty = 1  # Stockfish depth level
        
    def find_stockfish(self):
        """Find Stockfish executable in common locations"""
        possible_paths = [
            './stockfish.exe',  # Your local stockfish.exe
            './stockfish/stockfish.exe',  # If in stockfish subfolder
            'stockfish.exe',  # Current directory
            'stockfish',  # If in PATH
            './stockfish',
            '/usr/bin/stockfish',
            '/usr/local/bin/stockfish',
            'C:\\Program Files\\stockfish\\stockfish.exe',
            'C:\\stockfish\\stockfish.exe'
        ]
        
        for path in possible_paths:
            try:
                if os.path.exists(path) or path == 'stockfish':
                    logger.info(f"Found Stockfish at: {path}")
                    return path
            except Exception as e:
                logger.debug(f"Path {path} not accessible: {e}")
                continue
        
        logger.error("Stockfish executable not found in any common locations")
        return None
    
    def start_engine(self):
        """Initialize the chess engine"""
        try:
            if self.engine_path:
                self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
                logger.info(f"Stockfish engine started at {self.engine_path}")
                return True
            else:
                logger.error("Stockfish not found")
                return False
        except Exception as e:
            logger.error(f"Failed to start engine: {e}")
            return False
    
    def stop_engine(self):
        """Stop the chess engine"""
        if self.engine:
            self.engine.quit()
            self.engine = None
    
    def make_move(self, move_str):
        """Make a player move"""
        try:
            move = chess.Move.from_uci(move_str)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.game_history.append({
                    'move': move_str,
                    'player': 'human',
                    'timestamp': datetime.now().isoformat()
                })
                return True
            return False
        except:
            return False
    
    def get_engine_move(self):
        """Get AI move from Stockfish"""
        try:
            if not self.engine:
                if not self.start_engine():
                    return None
            
            result = self.engine.play(self.board, chess.engine.Limit(depth=self.difficulty))
            move = result.move
            self.board.push(move)
            
            self.game_history.append({
                'move': move.uci(),
                'player': 'ai',
                'timestamp': datetime.now().isoformat()
            })
            
            return move.uci()
        except Exception as e:
            logger.error(f"Engine move failed: {e}")
            return None
    
    def get_board_state(self):
        """Get current board state"""
        return {
            'fen': self.board.fen(),
            'turn': 'white' if self.board.turn else 'black',
            'is_check': self.board.is_check(),
            'is_checkmate': self.board.is_checkmate(),
            'is_stalemate': self.board.is_stalemate(),
            'is_game_over': self.board.is_game_over(),
            'legal_moves': [move.uci() for move in self.board.legal_moves],
            'move_count': len(self.game_history)
        }
    
    def reset_game(self):
        """Reset the game"""
        self.board = chess.Board()
        self.game_history = []
    
    def set_difficulty(self, level):
        """Set AI difficulty (1-20, higher is stronger)"""
        self.difficulty = max(1, min(20, level))

# Global game instance
game = ChessGame()

@app.route('/')
def index():
    """Serve the chess game frontend"""
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start_game():
    """Start a new chess game"""
    try:
        data = request.get_json() or {}
        difficulty = data.get('difficulty', 1)
        
        game.reset_game()
        game.set_difficulty(difficulty)
        
        if not game.start_engine():
            return jsonify({
                'success': False,
                'error': 'Could not start chess engine. Please ensure Stockfish is installed.'
            }), 500
        
        return jsonify({
            'success': True,
            'board_state': game.get_board_state()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/move', methods=['POST'])
def make_move():
    """Make a player move"""
    try:
        data = request.get_json()
        move = data.get('move')
        
        if not move:
            return jsonify({'success': False, 'error': 'Move required'}), 400
        
        # Make player move
        if not game.make_move(move):
            return jsonify({'success': False, 'error': 'Invalid move'}), 400
        
        board_state = game.get_board_state()
        
        # Check if game is over after player move
        if board_state['is_game_over']:
            return jsonify({
                'success': True,
                'board_state': board_state,
                'ai_move': None,
                'game_over': True
            })
        
        # Get AI response move
        ai_move = game.get_engine_move()
        if not ai_move:
            return jsonify({'success': False, 'error': 'AI move failed'}), 500
        
        return jsonify({
            'success': True,
            'board_state': game.get_board_state(),
            'ai_move': ai_move,
            'game_over': game.get_board_state()['is_game_over']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/board', methods=['GET'])
def get_board():
    """Get current board state"""
    try:
        return jsonify({
            'success': True,
            'board_state': game.get_board_state()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reset', methods=['POST'])
def reset_game():
    """Reset the current game"""
    try:
        game.reset_game()
        return jsonify({
            'success': True,
            'board_state': game.get_board_state()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/difficulty', methods=['POST'])
def set_difficulty():
    """Set AI difficulty"""
    try:
        data = request.get_json()
        level = data.get('level', 1)
        game.set_difficulty(level)
        
        return jsonify({
            'success': True,
            'difficulty': game.difficulty
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get game move history"""
    try:
        return jsonify({
            'success': True,
            'history': game.game_history,
            'pgn': game.board.pgn() if hasattr(game.board, 'pgn') else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.teardown_appcontext
def cleanup(error):
    """Cleanup resources"""
    if error:
        logger.error(f"Application error: {error}")

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        game.stop_engine()