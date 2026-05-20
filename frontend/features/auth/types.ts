export type AuthUser = {
  id: string;
  name: string;
  email: string;
  role?: string;
};

export type AuthCredentials = {
  name?: string;
  email: string;
  password: string;
};

export type AuthResponse = {
  user: AuthUser;
  token: string;
  token_type: string;
};
