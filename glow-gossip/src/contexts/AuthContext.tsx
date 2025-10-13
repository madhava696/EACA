import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, UserProfile } from '@/services/api';
import { toast } from 'sonner';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isGuest: boolean;
  guestMessageCount: number;
  isLoading: boolean;
  login: (email: string, password: string, secretKey: string) => Promise<boolean>;
  register: (email: string, password: string, secretKey: string) => Promise<boolean>;
  logout: () => void;
  continueAsGuest: () => void;
  incrementGuestCount: () => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const GUEST_MESSAGE_LIMIT = 20;
const GUEST_COUNT_KEY = 'guest_message_count';
const JWT_TOKEN_KEY = 'jwt_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isGuest, setIsGuest] = useState(false);
  const [guestMessageCount, setGuestMessageCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem(JWT_TOKEN_KEY);
      const guestMode = localStorage.getItem('guest_mode') === 'true';
      const savedCount = parseInt(localStorage.getItem(GUEST_COUNT_KEY) || '0');

      if (guestMode) {
        setIsGuest(true);
        setGuestMessageCount(savedCount);
        setIsLoading(false);
      } else if (token) {
        try {
          const response = await api.getProfile();
          if (response.data) {
            setUser(response.data);
          } else {
            localStorage.removeItem(JWT_TOKEN_KEY);
          }
        } catch (error) {
          console.error('Auth init error:', error);
          localStorage.removeItem(JWT_TOKEN_KEY);
        }
        setIsLoading(false);
      } else {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (email: string, password: string, secretKey: string): Promise<boolean> => {
    try {
      const response = await api.login({ email, password, secret_key: secretKey });
      
      if (response.token) {
        localStorage.setItem(JWT_TOKEN_KEY, response.token);
        const profileResponse = await api.getProfile();
        if (profileResponse.data) {
          setUser(profileResponse.data);
          toast.success('Logged in successfully!');
          return true;
        }
      } else {
        toast.error(response.error || 'Login failed');
        return false;
      }
    } catch (error) {
      toast.error('Login failed. Please check your credentials.');
      return false;
    }
    return false;
  };

  const register = async (email: string, password: string, secretKey: string): Promise<boolean> => {
    try {
      const response = await api.register({ email, password, secret_key: secretKey });
      
      if (response.message === 'User registered successfully') {
        toast.success('Registration successful! Please log in.');
        return true;
      } else {
        toast.error(response.error || 'Registration failed');
        return false;
      }
    } catch (error) {
      toast.error('Registration failed. Please try again.');
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem(JWT_TOKEN_KEY);
    localStorage.removeItem('guest_mode');
    localStorage.removeItem(GUEST_COUNT_KEY);
    setUser(null);
    setIsGuest(false);
    setGuestMessageCount(0);
    toast.success('Logged out successfully');
  };

  const continueAsGuest = () => {
    localStorage.setItem('guest_mode', 'true');
    localStorage.setItem(GUEST_COUNT_KEY, '0');
    setIsGuest(true);
    setGuestMessageCount(0);
    toast.success('Continuing as guest (20 messages limit)');
  };

  const incrementGuestCount = (): boolean => {
    if (!isGuest) return true;
    
    const newCount = guestMessageCount + 1;
    if (newCount > GUEST_MESSAGE_LIMIT) {
      toast.error('Guest limit reached. Please sign in to continue.');
      return false;
    }
    
    setGuestMessageCount(newCount);
    localStorage.setItem(GUEST_COUNT_KEY, newCount.toString());
    return true;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isGuest,
        guestMessageCount,
        isLoading,
        login,
        register,
        logout,
        continueAsGuest,
        incrementGuestCount,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
