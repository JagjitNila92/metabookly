import 'next-auth'
import 'next-auth/jwt'

declare module 'next-auth' {
  interface Session {
    idToken: string
    user: {
      id: string
      email: string
      name?: string | null
      image?: string | null
    }
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    idToken: string
  }
}
