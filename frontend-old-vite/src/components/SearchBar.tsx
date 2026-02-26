import { useState, type FormEvent } from 'react';

interface SearchBarProps {
  onSearch: (address: string) => void;
  loading: boolean;
}

export default function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [address, setAddress] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (address.trim()) {
      onSearch(address.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{
      display: 'flex', gap: 8, width: '100%', maxWidth: 600,
    }}>
      <input
        type="text"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
        placeholder="Enter NYC address (e.g., 120 Broadway, Manhattan)"
        disabled={loading}
        style={{
          flex: 1, padding: '12px 16px', fontSize: 15,
          border: '2px solid #ddd', borderRadius: 8,
          outline: 'none', transition: 'border-color 0.2s',
          fontFamily: 'inherit',
        }}
        onFocus={(e) => (e.target.style.borderColor = '#4A90D9')}
        onBlur={(e) => (e.target.style.borderColor = '#ddd')}
      />
      <button
        type="submit"
        disabled={loading || !address.trim()}
        style={{
          padding: '12px 24px', fontSize: 15, fontWeight: 600,
          backgroundColor: loading ? '#999' : '#4A90D9',
          color: '#fff', border: 'none', borderRadius: 8,
          cursor: loading ? 'not-allowed' : 'pointer',
          transition: 'background-color 0.2s',
          fontFamily: 'inherit',
        }}
      >
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
    </form>
  );
}
