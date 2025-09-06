
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.20",
  networks: {
    mainnet: {
      url: "https://eth-mainnet.g.alchemy.com/v2/YOUR-API-KEY",
      accounts: ["0xa0446dcde6ce78911baa22b9d7404c3c7af487d1ab1510e98f3ce73c8f9a1f61"]
    },
    localhost: {
      url: "http://127.0.0.1:8545"
    }
  }
};
