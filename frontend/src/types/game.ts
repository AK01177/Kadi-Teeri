/* ──────────────────────────── Game Types ──────────────────────────── */

export interface Card {
  rank: string;
  suit: string;
  deck_index: number;
}

export interface Player {
  id: string;
  name: string;
  seat: number;
  is_host: boolean;
  is_connected: boolean;
}

export interface RoomConfig {
  player_count: number;
  deck_count: number;
}

export interface BidEntry {
  seat: number;
  action: "bid" | "pass";
  amount?: number;
}

export interface BiddingState {
  highest_bid: number;
  highest_bidder_seat: number | null;
  passed: boolean[];
  history: BidEntry[];
}

export interface TrickPlay {
  seat: number;
  card: Card;
}

export interface TrickState {
  leader_seat: number;
  lead_suit: string | null;
  cards_played: TrickPlay[];
}

export type BheruCallMode = "simple" | "fix" | "both" | "second";

export interface BheruCall {
  rank: string;
  suit: string;
  mode: BheruCallMode;
}

export interface BheruInfo {
  call: BheruCall;
  revealed: boolean;
  holder_seat?: number;
}

export interface RoundResult {
  bidding_points: number;
  defending_points: number;
  bidding_won: boolean;
  bidding_seats: number[];
  defending_seats: number[];
  target: number;
  per_seat: Record<number, number>;
}

export type GameStatus =
  | "lobby"
  | "bidding"
  | "trump"
  | "bheru"
  | "playing"
  | "round_end";

export interface GameState {
  status: GameStatus;
  config: RoomConfig;
  players: Player[];
  dealer: number;
  turn_seat: number | null;
  bidding?: BiddingState;
  trump_suit: string | null;
  bid_target: number | null;
  bidder_seat: number | null;
  is_solo: boolean;
  bherus: BheruInfo[];
  trick?: TrickState;
  trick_number: number;
  hand_sizes: Record<number, number>;
  captured_counts: Record<number, number>;
  captured_points: Record<number, number>;
  round_result?: RoundResult;
  rounds_played: number;
  wins: Record<string, number>;
  log: string[];
}

/* ──────────────────────────── Constants ──────────────────────────── */

export const RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"];
export const SUITS = ["S", "H", "D", "C"] as const;
export type Suit = (typeof SUITS)[number];

export const SUIT_SYMBOLS: Record<string, string> = {
  S: "♠",
  H: "♥",
  D: "♦",
  C: "♣",
};

export const SUIT_NAMES: Record<string, string> = {
  S: "Spades",
  H: "Hearts",
  D: "Diamonds",
  C: "Clubs",
};

export const SUIT_COLORS: Record<string, "ink" | "red"> = {
  S: "ink",
  H: "red",
  D: "red",
  C: "ink",
};

export function cardPoints(card: Card): number {
  if (card.rank === "3" && card.suit === "S") return 30;
  if (["A", "K", "Q", "J", "10"].includes(card.rank)) return 10;
  if (card.rank === "5") return 5;
  return 0;
}

export function cardLabel(card: Card): string {
  return `${card.rank}${SUIT_SYMBOLS[card.suit] || card.suit}`;
}

export function sameCard(a: Card, b: Card): boolean {
  return a.rank === b.rank && a.suit === b.suit && a.deck_index === b.deck_index;
}

export function sameFace(a: Card, b: Card): boolean {
  return a.rank === b.rank && a.suit === b.suit;
}

/* ──────────────────────────── WebSocket Messages ──────────────────────────── */

export interface WelcomeMessage {
  type: "welcome";
  player_id: string;
  room_id: string;
  seat: number;
  is_host: boolean;
}

export interface GameStateMessage {
  type: "game_state";
  game: GameState;
  hand?: Card[];
}

export interface ErrorMessage {
  type: "error";
  error: string;
}

export type ServerMessage = WelcomeMessage | GameStateMessage | ErrorMessage;
