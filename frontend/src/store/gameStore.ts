import { create } from "zustand";
import type {
  GameState,
  Card,
  BheruCall,
} from "../types/game";

interface GameStore {
  // Connection
  isConnected: boolean;
  setConnected: (v: boolean) => void;
  connectionMode: "online" | "local";
  setConnectionMode: (v: "online" | "local") => void;

  // Identity
  playerId: string | null;
  playerName: string | null;
  roomId: string | null;
  seat: number | null;
  isHost: boolean;

  setIdentity: (data: {
    playerId: string;
    roomId: string;
    seat: number;
    isHost: boolean;
  }) => void;
  setPlayerName: (name: string) => void;

  // Game State (from server)
  gameState: GameState | null;
  hand: Card[];
  setGameState: (game: GameState, hand?: Card[]) => void;

  trickWinner: { name: string; points: number } | null;
  setTrickWinner: (v: { name: string; points: number } | null) => void;

  // View Settings
  is3DView: boolean;
  setIs3DView: (v: boolean) => void;

  // Local UI state
  pendingBid: number | null;
  setPendingBid: (v: number | null) => void;

  selectedTrump: string | null;
  setSelectedTrump: (v: string | null) => void;

  bheruTabSuit: string;
  setBheruTabSuit: (v: string) => void;

  selectedBheruCalls: BheruCall[];
  setSelectedBheruCalls: (v: BheruCall[]) => void;
  addBheruCall: (call: BheruCall) => void;
  removeBheruCall: (rank: string, suit: string) => void;

  toast: string | null;
  showToast: (msg: string) => void;
  clearToast: () => void;

  // Actions
  reset: () => void;
  leaveRoom: () => void;

  // Send function reference (set by the App component)
  sendFn: ((data: Record<string, unknown>) => void) | null;
  setSendFn: (fn: (data: Record<string, unknown>) => void) => void;
}

const sessionStr = localStorage.getItem("kadi_session");
let session = null;
try {
  if (sessionStr) session = JSON.parse(sessionStr);
} catch (e) {
  // ignore
}

export const useGameStore = create<GameStore>((set, get) => ({
  // Connection
  isConnected: false,
  setConnected: (v) => set({ isConnected: v }),
  connectionMode: "online",
  setConnectionMode: (v) => set({ connectionMode: v }),

  // Identity
  playerId: session?.playerId || null,
  playerName: session?.playerName || localStorage.getItem("kadi_player_name"),
  roomId: session?.roomId || null,
  seat: null,
  isHost: false,

  setIdentity: (data) =>
    set({
      playerId: data.playerId,
      roomId: data.roomId,
      seat: data.seat,
      isHost: data.isHost,
    }),
  setPlayerName: (name) => {
    localStorage.setItem("kadi_player_name", name);
    set({ playerName: name });
  },

  // Game State
  gameState: null,
  hand: [],
  setGameState: (game, hand) => {
    const state = get();
    // Update seat and host from server state
    const me = game.players.find((p) => p.id === state.playerId);
    set({
      gameState: game,
      hand: hand || state.hand,
      seat: me?.seat ?? state.seat,
      isHost: me?.is_host ?? state.isHost,
      trickWinner: null,
    });
  },

  trickWinner: null,
  setTrickWinner: (v) => set({ trickWinner: v }),

  // View Settings
  is3DView: true,
  setIs3DView: (v) => set({ is3DView: v }),

  // Local UI state
  pendingBid: null,
  setPendingBid: (v) => set({ pendingBid: v }),

  selectedTrump: null,
  setSelectedTrump: (v) => set({ selectedTrump: v }),

  bheruTabSuit: "S",
  setBheruTabSuit: (v) => set({ bheruTabSuit: v }),

  selectedBheruCalls: [],
  setSelectedBheruCalls: (v) => set({ selectedBheruCalls: v }),
  addBheruCall: (call) =>
    set((s) => ({
      selectedBheruCalls: [
        ...s.selectedBheruCalls.filter(
          (c) => !(c.rank === call.rank && c.suit === call.suit)
        ),
        call,
      ],
    })),
  removeBheruCall: (rank, suit) =>
    set((s) => ({
      selectedBheruCalls: s.selectedBheruCalls.filter(
        (c) => !(c.rank === rank && c.suit === suit)
      ),
    })),

  toast: null,
  showToast: (msg) => {
    set({ toast: msg });
    setTimeout(() => {
      set((s) => (s.toast === msg ? { toast: null } : {}));
    }, 3000);
  },
  clearToast: () => set({ toast: null }),

  // Actions
  reset: () => {
    localStorage.removeItem("kadi_session");
    set({
      playerId: null,
      roomId: null,
      seat: null,
      isHost: false,
      gameState: null,
      hand: [],
      pendingBid: null,
      selectedTrump: null,
      bheruTabSuit: "S",
      selectedBheruCalls: [],
      isConnected: false,
      connectionMode: "online",
    });
  },

  leaveRoom: () => {
    localStorage.removeItem("kadi_session");
    set({
      roomId: null,
      seat: null,
      isHost: false,
      gameState: null,
      hand: [],
      pendingBid: null,
      selectedTrump: null,
      bheruTabSuit: "S",
      selectedBheruCalls: [],
    });
  },

  // Send function
  sendFn: null,
  setSendFn: (fn) => set({ sendFn: fn }),
}));
