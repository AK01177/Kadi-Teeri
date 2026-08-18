import { describe, it, expect, beforeEach } from 'vitest';
import { useGameStore } from './gameStore';

describe('gameStore', () => {
  beforeEach(() => {
    useGameStore.getState().reset();
  });

  it('should initialize correctly', () => {
    const state = useGameStore.getState();
    expect(state.isConnected).toBe(false);
    expect(state.roomId).toBe(null);
  });

  it('should set identity', () => {
    useGameStore.getState().setIdentity({
      playerId: "p1",
      roomId: "r1",
      seat: 0,
      isHost: true
    });
    const state = useGameStore.getState();
    expect(state.playerId).toBe("p1");
    expect(state.roomId).toBe("r1");
    expect(state.seat).toBe(0);
    expect(state.isHost).toBe(true);
  });

  it('should update state and recalculate seat without mutating player identity on refresh', () => {
    useGameStore.getState().setIdentity({
      playerId: "p1",
      roomId: "r1",
      seat: 0,
      isHost: false
    });
    useGameStore.getState().setIsRefreshing(true);
    expect(useGameStore.getState().isRefreshing).toBe(true);

    const mockGame: any = {
      status: "playing",
      players: [
        { id: "p1", name: "Player 1", seat: 2, is_host: true },
        { id: "p2", name: "Player 2", seat: 0, is_host: false }
      ]
    };
    const mockHand: any[] = [{ rank: "A", suit: "S", deck_index: 0 }];

    useGameStore.getState().setGameState(mockGame, mockHand);

    const updated = useGameStore.getState();
    expect(updated.gameState).toEqual(mockGame);
    expect(updated.hand).toEqual(mockHand);
    expect(updated.seat).toBe(2);
    expect(updated.isHost).toBe(true);
    expect(updated.playerId).toBe("p1");
    expect(updated.roomId).toBe("r1");
    expect(updated.isRefreshing).toBe(false);
  });

  it('should handle isReconnecting state and clear flags on state update', () => {
    useGameStore.getState().setIsReconnecting(true);
    expect(useGameStore.getState().isReconnecting).toBe(true);

    const mockGame: any = {
      status: "lobby",
      players: [{ id: "p1", name: "Player 1", seat: 0, is_host: true }]
    };

    useGameStore.getState().setGameState(mockGame);

    const updated = useGameStore.getState();
    expect(updated.isReconnecting).toBe(false);
    expect(updated.isRefreshing).toBe(false);
  });
});
