import { configureStore } from '@reduxjs/toolkit';
import relayReducer from './slices/relaySlice';

export const store = configureStore({
  reducer: {
    relay: relayReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

import { useDispatch, useSelector, TypedUseSelectorHook } from 'react-redux';
export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
