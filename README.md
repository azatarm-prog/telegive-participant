# Participant Management Service (`telegive-participant`)

This is the complete documentation for the Participant Management Service, a core component of the Telegive microservices ecosystem. This service is responsible for managing user participation in giveaways, handling a global math captcha system for new users, ensuring fair and transparent winner selection, and tracking user participation history.

## 🚀 Core Features

*   **Participation Management**: Securely tracks user participation in each giveaway, ensuring that each user can only participate once.
*   **Global Captcha System**: Implements a mandatory math captcha for all first-time users across the entire Telegive platform. Once a user completes the captcha, they are not required to do so again.
*   **Cryptographically Secure Winner Selection**: Uses the `secrets` module in Python to ensure that winner selection is truly random and cannot be manipulated.
*   **Subscription Verification**: Integrates with the Telegram Bot API to verify that a user is subscribed to the required channel before they can participate.
*   **Participation History**: Maintains a comprehensive history of each user's participation across all giveaways, including their total number of participations and wins.
*   **Detailed Auditing**: Logs all critical operations, including winner selections, for transparency and auditing purposes.
*   **Inter-Service Communication**: Seamlessly integrates with other Telegive services, including the Auth, Channel, and Giveaway services.

## 🛠️ Technology Stack

*   **Framework**: Flask (Python)
*   **Database**: PostgreSQL (shared with other services)
*   **Cryptography**: `secrets` module for secure random number generation
*   **External API**: Telegram Bot API
*   **Caching**: Redis (optional, for captcha session management)
*   **Deployment**: Railway

## ⚙️ Setup and Installation

To set up and run this service locally, follow these steps:

1.  **Clone the repository**:

    ```bash
    git clone https://github.com/YOUR_USERNAME/telegive-participant.git
    cd telegive-participant
    ```

2.  **Create a virtual environment**:

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**:

    Create a `.env` file by copying the `.env.example` file and filling in the required values:

    ```bash
    cp .env.example .env
    ```

    You will need to provide the following:

    *   `DATABASE_URL`: The connection string for your PostgreSQL database.
    *   `SECRET_KEY`: A secret key for Flask sessions and security.
    *   URLs for other Telegive services (`TELEGIVE_AUTH_URL`, `TELEGIVE_CHANNEL_URL`, `TELEGIVE_GIVEAWAY_URL`).

5.  **Run the application**:

    ```bash
    flask run
    ```

    The service will be available at `http://127.0.0.1:8004` by default.

## 🧪 Running Tests

To run the comprehensive test suite, use the following command:

```bash
pytest
```

This will execute all unit, integration, and performance tests.

## 🔗 API Endpoints

This service exposes a number of API endpoints for managing participants, captchas, and winner selections. All endpoints are prefixed with `/api/participants`.

For detailed information on each endpoint, including request and response formats, please refer to the `ParticipantManagementService-CompleteDevelopmentSpecification.md` document.

## 📜 License

This project is licensed under the MIT License. See the `LICENSE` file for details.


