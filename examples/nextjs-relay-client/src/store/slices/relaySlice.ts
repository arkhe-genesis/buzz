import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

interface RelayState {
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  events: Record<string, any>; // Indexado pelo ID do evento Nostr
  authChallenge: string | null;
}

const initialState: RelayState = {
  connectionStatus: 'disconnected',
  events: {},
  authChallenge: null,
};

export const relaySlice = createSlice({
  name: 'relay',
  initialState,
  reducers: {
    setConnectionStatus: (state, action: PayloadAction<RelayState['connectionStatus']>) => {
      state.connectionStatus = action.payload;
    },
    addEvent: (state, action: PayloadAction<any>) => {
      // Evita duplicatas no estado (Nostr pode enviar o mesmo evento múltiplas vezes)
      if (!state.events[action.payload.id]) {
        state.events[action.payload.id] = action.payload;
      }
    },
    setAuthChallenge: (state, action: PayloadAction<string>) => {
      state.authChallenge = action.payload;
    },
  },
});

export const { setConnectionStatus, addEvent, setAuthChallenge } = relaySlice.actions;
export default relaySlice.reducer;
