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
});
