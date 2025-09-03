.PHONY: help install build test deploy clean dev prod docker-up docker-down

help:
	@echo "QXC Token Ecosystem - Available Commands"
	@echo "========================================"
	@echo "make install    - Install dependencies"
	@echo "make build      - Compile contracts"
	@echo "make test       - Run test suite"
	@echo "make deploy     - Deploy to network"
	@echo "make dev        - Start development server"
	@echo "make prod       - Start production server"
	@echo "make docker-up  - Start Docker services"
	@echo "make docker-down- Stop Docker services"
	@echo "make clean      - Clean build artifacts"

install:
	npm install

build:
	npx hardhat compile

test:
	npm test

coverage:
	npx hardhat coverage

deploy:
	npx hardhat run scripts/deploy.js --network mainnet

deploy-testnet:
	npx hardhat run scripts/deploy.js --network goerli

dev:
	npx hardhat node & npm run dev

prod:
	npm start

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

clean:
	rm -rf artifacts cache coverage coverage.json node_modules

audit:
	npm audit fix

format:
	npm run format

lint:
	npm run lint

verify:
	npx hardhat verify --network mainnet