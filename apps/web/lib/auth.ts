import { AuthOptions } from 'next-auth'
import CredentialsProvider from 'next-auth/providers/credentials'
import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
} from '@aws-sdk/client-cognito-identity-provider'

const cognito = new CognitoIdentityProviderClient({ region: 'eu-west-2' })

export const authOptions: AuthOptions = {
  providers: [
    CredentialsProvider({
      name: 'Retailer Account',
      credentials: {
        email: { label: 'Email', type: 'email', placeholder: 'you@yourshop.com' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null

        try {
          const response = await cognito.send(
            new InitiateAuthCommand({
              AuthFlow: 'USER_PASSWORD_AUTH',
              ClientId: process.env.COGNITO_CLIENT_ID!,
              AuthParameters: {
                USERNAME: credentials.email,
                PASSWORD: credentials.password,
              },
            }),
          )

          const tokens = response.AuthenticationResult
          if (!tokens?.IdToken) return null

          // Decode the ID token payload (base64url → JSON) to extract sub + email
          const payload = JSON.parse(
            Buffer.from(tokens.IdToken.split('.')[1], 'base64url').toString(),
          )

          return {
            id: payload.sub as string,
            email: credentials.email,
            name: payload.name ?? credentials.email,
            // Pass the Cognito ID token through so we can forward it to the API
            idToken: tokens.IdToken,
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : String(err)
          // NotAuthorizedException = wrong password; UserNotFoundException = unknown user
          console.warn('Cognito auth failed:', msg)
          return null
        }
      },
    }),
  ],

  session: { strategy: 'jwt' },

  callbacks: {
    async jwt({ token, user }) {
      // `user` is only set on the first sign-in
      if (user) {
        token.idToken = (user as unknown as { idToken: string }).idToken
        token.sub = user.id
      }
      return token
    },
    async session({ session, token }) {
      // Expose the Cognito ID token on the session for API calls
      session.idToken = token.idToken as string
      if (session.user) {
        session.user.id = token.sub as string
      }
      return session
    },
  },

  pages: {
    signIn: '/login',
    error: '/login',
  },
}
