# Metabookly

AI-powered book discovery and ordering platform for book retailers.

## Structure

```
metabookly/
├── apps/
│   ├── web/          # Next.js frontend (TypeScript)
│   └── api/          # FastAPI backend (Python)
├── infra/            # AWS CDK infrastructure (TypeScript)
├── packages/
│   └── shared/       # Shared types and utilities
├── docs/             # Technical documentation
└── .github/
    └── workflows/    # CI/CD pipelines
```

## Tech Stack

- **Frontend**: Next.js 14 (TypeScript)
- **Backend**: Python FastAPI
- **Database**: Aurora Serverless v2 (PostgreSQL)
- **Search**: Amazon OpenSearch Service
- **Cache**: ElastiCache Redis
- **AI**: AWS Bedrock (Claude)
- **Storage**: Amazon S3
- **Auth**: Amazon Cognito
- **Infrastructure**: AWS CDK (TypeScript)
- **Region**: eu-west-2 (London)

## Getting Started

See [docs/setup.md](docs/setup.md) for local development setup.
