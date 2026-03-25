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
          if (!tokens?.IdToken || !tokens?.AccessToken) return null

          // Decode the ID token payload to extract sub + email (ID token has user attributes)
          const payload = JSON.parse(
            Buffer.from(tokens.IdToken.split('.')[1], 'base64url').toString(),
          )

          // Decode access token to extract Cognito groups
          const accessPayload = JSON.parse(
            Buffer.from(tokens.AccessToken.split('.')[1], 'base64url').toString(),
          )
          const groups: string[] = accessPayload['cognito:groups'] ?? []

          return {
            id: payload.sub as string,
            email: credentials.email,
            name: payload.name ?? credentials.email,
            accessToken: tokens.AccessToken,
            groups,
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
      if (user) {
        const u = user as unknown as { accessToken: string; groups: string[] }
        token.accessToken = u.accessToken
        token.sub = user.id
        token.groups = u.groups
      }
      return token
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string
      session.groups = (token.groups as string[]) ?? []
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
