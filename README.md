Skribbl.io Recreation
Developer: Ido Fishman

A multi-threaded drawing and guessing game implemented in Python. The system utilizes a client-server architecture over TCP sockets to facilitate real-time synchronization and secure data exchange between multiple concurrent users.
Technical Overview
Asynchronous Communication: Employs the socket and threading modules to manage concurrent network I/O, ensuring a responsive user experience by decoupling network events from the UI thread.

Security Architecture:
Key Exchange: Implements a custom Diffie-Hellman handshake to establish unique shared secrets for every session.
Encrypted Payloads: Leverages AES-GCM (Authenticated Encryption with Associated Data) to secure sensitive game data, such as word guesses, protecting against packet interception.
Reliable Data Framing: Uses a dedicated utility (tcp_by_size.py) to implement message length prefixing, ensuring atomic delivery of data packets across TCP byte streams.
Graphic Rendering Engine: Developed using wxPython, featuring a double-buffered canvas supporting freehand drawing, a flood-fill algorithm for regional coloring, and state management for Undo functionality.
Media Integration: Integrates background audio via the pygame.mixer engine.

Project Structure
server.py: Acts as the central authority for game state, word library management, and cryptographic coordination.
client.py: The user-facing application handling local event processing, GUI rendering, and encrypted upstream communication.
tcp_by_size.py: Low-level network abstraction layer for consistent data transmission.

Getting Started
Prerequisites
The environment requires Python 3.x and the following dependencies. Run this command in your terminal:
pip install wxPython pygame cryptography

Execution
Host the Session: Initialize server.py. Configure the session parameters—rounds, duration per round, and expected player count—in the setup dialog.
Join the Game: Launch client.py on participant machines. Provide a unique username and the host's IP address (local testing defaults to 127.0.0.1) to authenticate and synchronize with the server.

Security Protocol
Immediately upon connection, the system performs a SHA-256 hashed Diffie-Hellman exchange. The resulting key is used for all subsequent AESGCM encryption routines, ensuring that all game-critical communication remains confidential and tamper-proof.