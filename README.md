# RHCP Chatbot

A specialized chatbot for Red Hot Chili Peppers fans, providing information about the band's history, music, and members.

## Features

- Chat interface for interacting with the RHCP knowledge base
- User authentication and authorization
- Admin panel for managing knowledge base content
- RESTful API for integration with other applications
- PostgreSQL database for data persistence

## Prerequisites

- Node.js >= 14.0.0
- PostgreSQL >= 12.0
- npm or yarn package manager

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/rhcp-chatbot.git
   cd rhcp-chatbot
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file in the root directory with the following variables:
   ```
   NODE_ENV=development
   PORT=3000
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=rhcp_chatbot
   DB_USER=your_username
   DB_PASSWORD=your_password
   JWT_SECRET=your_jwt_secret
   ```

4. Create the database:
   ```bash
   createdb rhcp_chatbot
   ```

5. Run database migrations:
   ```bash
   npx sequelize-cli db:migrate
   ```

6. Seed the database with initial data:
   ```bash
   npm run seed
   ```

## Development

Start the development server with hot reloading:
```bash
npm run dev
```

## Production

Start the production server:
```bash
npm start
```

## API Endpoints

### Authentication
- `POST /api/users/register` - Register a new user
- `POST /api/users/login` - Login user

### User Management
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update user profile
- `PUT /api/users/password` - Update user password

### Chat
- `POST /api/chat` - Send a message to the chatbot
- `GET /api/chat/history` - Get chat history

### Knowledge Base
- `GET /api/knowledge` - Search knowledge base
- `GET /api/knowledge/:id` - Get knowledge entry by ID
- `POST /api/knowledge` - Create knowledge entry (admin only)
- `PUT /api/knowledge/:id` - Update knowledge entry (admin only)
- `DELETE /api/knowledge/:id` - Delete knowledge entry (admin only)

## Testing

Run the test suite:
```bash
npm test
```

## Linting and Formatting

Run ESLint:
```bash
npm run lint
```

Format code with Prettier:
```bash
npm run format
```

## Project Structure

```
rhcp-chatbot/
├── src/                           # Node.js implementation
│   ├── http/
│   │   ├── controllers/
│   │   └── routes/
│   ├── data/ 
│   │   ├── static/               # Band info, discography
│   │   └── training/             # Training corpus
│   ├── initializer.js
│   ├── chatbotProcessor.js
│   └── app.js
├── rhcp-chatbot-py/              # Python implementation
│   ├── app/
│   │   ├── api/
│   │   ├── chatbot/
│   │   └── core/
│   └── requirements.txt
├── docs/                         # Comprehensive documentation
│   ├── README.md                 # Documentation index
│   ├── API_DOCUMENTATION.md      # API reference
│   ├── COMPONENT_DOCUMENTATION.md # Component reference
│   ├── USAGE_GUIDE.md           # User guide
│   └── DEVELOPMENT_GUIDE.md     # Developer guide
├── test/                         # Test files
├── .env
├── .gitignore
├── package.json
└── README.md
```

## Documentation

📚 **Comprehensive documentation is available in the [`docs/`](./docs/) directory:**

- **[Documentation Index](./docs/README.md)** - Start here for an overview of all documentation
- **[API Documentation](./docs/API_DOCUMENTATION.md)** - Complete API reference with examples
- **[Component Documentation](./docs/COMPONENT_DOCUMENTATION.md)** - Detailed component and function reference
- **[Usage Guide](./docs/USAGE_GUIDE.md)** - Installation, configuration, and usage examples
- **[Development Guide](./docs/DEVELOPMENT_GUIDE.md)** - Architecture, development setup, and contribution guidelines

## Contributing

We welcome contributions! Please see our [Development Guide](./docs/DEVELOPMENT_GUIDE.md) for detailed information on:

- Development setup and workflow
- Coding standards and best practices
- Testing procedures
- Pull request guidelines

Quick start for contributors:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature-name`)
3. Follow the coding standards in the development guide
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'feat: Add some feature'`)
6. Push to the branch (`git push origin feature/your-feature-name`)
7. Open a Pull Request

## License

This project is licensed under the ISC License.
