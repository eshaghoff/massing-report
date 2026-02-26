import axios from 'axios';
import type { CalculationResult, LotProfile } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

export async function lookupAddress(address: string): Promise<CalculationResult> {
  const resp = await api.get('/api/lookup', { params: { address } });
  return resp.data;
}

export async function getLot(bbl: string): Promise<LotProfile> {
  const resp = await api.get(`/api/lot/${bbl}`);
  return resp.data;
}

export async function calculateZoning(lotProfile: LotProfile): Promise<CalculationResult> {
  const resp = await api.post('/api/calculate', lotProfile);
  return resp.data;
}

export async function getMassing(bbl: string) {
  const resp = await api.get(`/api/massing/${bbl}`);
  return resp.data;
}

export async function createAssemblage(bbls: string[]) {
  const resp = await api.post('/api/assemblage', { bbls });
  return resp.data;
}
