import "../../styles/room/WaitingRoom.css";

interface WaitingRoomProps {
    players: string[];
    role: "host" | "player";
    onStart: () => void;
}

export function WaitingRoom({ players, role, onStart }: WaitingRoomProps) {
    return (
        <div className="mq-waiting-container">
            <div className="mq-waiting-header">
                <h2 className="mq-waiting-title">Waiting Room</h2>
                <div className="mq-player-count">
                    <strong>{players.length}</strong> players joined
                </div>
            </div>

            <div className="mq-players-grid">
                {players.map((p, i) => (
                    <div key={i} className="mq-player-pill">
                        <div className="mq-avatar-circle">
                            {p.charAt(0).toUpperCase()}
                        </div>
                        <div className="mq-player-details">
                            <span className="mq-p-name">{p}</span>
                        </div>
                        <div className="mq-status-dot active" />
                    </div>
                ))}
            </div>

            {role === "host" ? (
                <div className="mq-host-actions">
                    <button 
                        className="mq-btn-primary-lg mq-btn-full-width" 
                        onClick={onStart}
                        disabled={players.length === 0}
                    >
                        Launch Quiz Now
                    </button>
                    <p className="mq-host-hint">Only you can start the game as the host</p>
                </div>
            ) : (
                <div className="mq-player-waiting-msg">
                    <div className="mq-loader-dots"><span></span><span></span><span></span></div>
                    <p>Waiting for the host to start the game...</p>
                </div>
            )}
        </div>
    );
}