import { useEffect, useRef } from "react";
import { useGameStore } from "../store/gameStore";

// Audio instances (cached so they can be replayed quickly without reloading)
const cardPlayAudio = new Audio("/sounds/card_play.mp3");
const yourTurnAudio = new Audio("/sounds/your_turn.mp3");
const trickWonAudio = new Audio("/sounds/trick_won.mp3");
const gameOverAudio = new Audio("/sounds/game_over.mp3");
const playerJoinAudio = new Audio("/sounds/player_join.mp3");
const gameStartAudio = new Audio("/sounds/game_start.mp3");
const bidClickAudio = new Audio("/sounds/bid_click.mp3");

// Preload the audio files
cardPlayAudio.preload = "auto";
yourTurnAudio.preload = "auto";
trickWonAudio.preload = "auto";
gameOverAudio.preload = "auto";
playerJoinAudio.preload = "auto";
gameStartAudio.preload = "auto";
bidClickAudio.preload = "auto";

export function useSoundEffects() {
  const { gameState, seat, trickWinner, pendingBid } = useGameStore();
  
  const prevTurnSeat = useRef<number | null>(null);
  const prevCardsPlayedCount = useRef<number>(0);
  const prevTrickWinner = useRef<string | null>(null);
  const prevGameStatus = useRef<string | null>(null);
  const prevConnectedCount = useRef<number>(0);
  const prevPendingBid = useRef<number | null>(null);

  useEffect(() => {
    if (!gameState || seat === null) return;

    // Check for player joins
    const currentConnectedCount = gameState.players.filter(p => p.is_connected).length;
    if (currentConnectedCount > prevConnectedCount.current && gameState.status === "lobby") {
      playerJoinAudio.currentTime = 0;
      playerJoinAudio.play().catch(() => {});
    }
    prevConnectedCount.current = currentConnectedCount;

    // Check for game start
    if (gameState.status === "bidding" && prevGameStatus.current === "lobby") {
      gameStartAudio.currentTime = 0;
      gameStartAudio.play().catch(() => {});
    }

    // Check for bid adjustment
    if (pendingBid !== null && prevPendingBid.current !== null && pendingBid !== prevPendingBid.current) {
      bidClickAudio.currentTime = 0;
      bidClickAudio.play().catch(() => {});
      // Optional subtle haptic for bid click
      if (typeof navigator !== "undefined" && navigator.vibrate) {
        navigator.vibrate(10); 
      }
    }
    prevPendingBid.current = pendingBid;

    // 1. Check for card played
    const currentCardsCount = gameState.trick?.cards_played.length || 0;
    if (
      currentCardsCount > prevCardsPlayedCount.current &&
      gameState.status === "playing"
    ) {
      // A new card was played
      cardPlayAudio.currentTime = 0;
      cardPlayAudio.play().catch(() => {}); // catch needed because browsers block autoplay without interaction
    }
    prevCardsPlayedCount.current = currentCardsCount;

    // 2. Check for your turn
    if (
      gameState.turn_seat === seat &&
      prevTurnSeat.current !== seat &&
      gameState.status === "playing"
    ) {
      yourTurnAudio.currentTime = 0;
      yourTurnAudio.play().catch(() => {});
      
      // Haptic feedback (vibrate 50ms)
      if (typeof navigator !== "undefined" && navigator.vibrate) {
        navigator.vibrate(50);
      }
    }
    prevTurnSeat.current = gameState.turn_seat;

    // 3. Check for trick won
    if (trickWinner && prevTrickWinner.current !== trickWinner.name) {
      trickWonAudio.currentTime = 0;
      trickWonAudio.play().catch(() => {});
      
      // Extra happy haptics if *we* won the trick
      if (trickWinner.name === gameState.players[seat]?.name) {
        if (typeof navigator !== "undefined" && navigator.vibrate) {
          navigator.vibrate([30, 50, 30]); // double pulse
        }
      }
    }
    prevTrickWinner.current = trickWinner ? trickWinner.name : null;

    // 4. Check for round over
    if (
      gameState.status === "round_end" &&
      prevGameStatus.current === "playing"
    ) {
      gameOverAudio.currentTime = 0;
      gameOverAudio.play().catch(() => {});
      
      if (typeof navigator !== "undefined" && navigator.vibrate) {
        navigator.vibrate([100, 50, 100, 50, 200]); // long success vibration
      }
    }
    prevGameStatus.current = gameState.status;

  }, [gameState, seat, trickWinner, pendingBid]);
}
