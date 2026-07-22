import "../../styles/room/Leaderboard.css";
import { Crown } from "lucide-react";

interface LeaderboardEntry {
    name: string;
    score: number;
}

interface LeaderboardViewProps {
    leaderboard: LeaderboardEntry[];
    isFinal: boolean;
}

export function LeaderboardView({ leaderboard, isFinal }: LeaderboardViewProps) {
    if (leaderboard.length === 0) return null;

    return (
        <div className="mq-leaderboard-container">
            <h2 className="mq-leaderboard-header">
                {isFinal ? "Final Results" : "Leaderboard"}
            </h2>

            <div className="mq-podium-section">
                {/* 2nd Place */}
                {leaderboard[1] && (
                    <div className="mq-podium-spot second">
                        <div className="mq-podium-avatar">{leaderboard[1].name.charAt(0)}</div>
                        <div className="mq-podium-name">{leaderboard[1].name}</div>
                        <div className="mq-podium-pillar">
                            <span className="mq-podium-score">{leaderboard[1].score}</span>
                            <span className="mq-rank-number">2</span>
                        </div>
                    </div>
                )}

                {/* 1st Place */}
                {leaderboard[0] && (
                    <div className="mq-podium-spot first">
                        <div className="mq-podium-avatar">
                            <Crown size={28} className="mq-crown-icon" />
                        </div>
                        <div className="mq-podium-name">{leaderboard[0].name}</div>
                        <div className="mq-podium-pillar">
                            <span className="mq-podium-score">{leaderboard[0].score}</span>
                            <span className="mq-rank-number">1</span>
                        </div>
                    </div>
                )}

                {/* 3rd Place */}
                {leaderboard[2] && (
                    <div className="mq-podium-spot third">
                        <div className="mq-podium-avatar">{leaderboard[2].name.charAt(0)}</div>
                        <div className="mq-podium-name">{leaderboard[2].name}</div>
                        <div className="mq-podium-pillar">
                            <span className="mq-podium-score">{leaderboard[2].score}</span>
                            <span className="mq-rank-number">3</span>
                        </div>
                    </div>
                )}
            </div>

            <div className="mq-leaderboard-list">
                {leaderboard.slice(3).map((entry, i) => (
                    <div key={i} className="mq-leaderboard-row">
                        <span className="mq-row-rank">#{i + 4}</span>
                        <span className="mq-row-name">{entry.name}</span>
                        <span className="mq-row-score">{entry.score} pts</span>
                    </div>
                ))}
            </div>
        </div>
    );
}