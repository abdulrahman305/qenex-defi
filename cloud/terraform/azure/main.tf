terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  required_version = ">= 1.0"
}

provider "azurerm" {
  features {}
}

variable "location" {
  description = "Azure region"
  default     = "East US"
}

variable "vm_size" {
  description = "VM size"
  default     = "Standard_D2s_v3"
}

# Resource Group
resource "azurerm_resource_group" "qenex" {
  name     = "qenex-os-rg"
  location = var.location
}

# Virtual Network
resource "azurerm_virtual_network" "qenex" {
  name                = "qenex-os-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.qenex.location
  resource_group_name = azurerm_resource_group.qenex.name
}

resource "azurerm_subnet" "qenex" {
  name                 = "qenex-os-subnet"
  resource_group_name  = azurerm_resource_group.qenex.name
  virtual_network_name = azurerm_virtual_network.qenex.name
  address_prefixes     = ["10.0.1.0/24"]
}

# Public IP
resource "azurerm_public_ip" "qenex" {
  name                = "qenex-os-pip"
  location            = azurerm_resource_group.qenex.location
  resource_group_name = azurerm_resource_group.qenex.name
  allocation_method   = "Static"
  sku                = "Standard"
}

# Network Security Group
resource "azurerm_network_security_group" "qenex" {
  name                = "qenex-os-nsg"
  location            = azurerm_resource_group.qenex.location
  resource_group_name = azurerm_resource_group.qenex.name

  security_rule {
    name                       = "SSH"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTP"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTPS"
    priority                   = 1003
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "API"
    priority                   = 1004
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8000"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Network Interface
resource "azurerm_network_interface" "qenex" {
  name                = "qenex-os-nic"
  location            = azurerm_resource_group.qenex.location
  resource_group_name = azurerm_resource_group.qenex.name

  ip_configuration {
    name                          = "internal"
    subnet_id                     = azurerm_subnet.qenex.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.qenex.id
  }
}

resource "azurerm_network_interface_security_group_association" "qenex" {
  network_interface_id      = azurerm_network_interface.qenex.id
  network_security_group_id = azurerm_network_security_group.qenex.id
}

# Virtual Machine
resource "azurerm_linux_virtual_machine" "qenex" {
  name                = "qenex-os-vm"
  resource_group_name = azurerm_resource_group.qenex.name
  location            = azurerm_resource_group.qenex.location
  size                = var.vm_size

  admin_username = "azureuser"
  
  admin_ssh_key {
    username   = "azureuser"
    public_key = file("~/.ssh/id_rsa.pub")
  }

  network_interface_ids = [
    azurerm_network_interface.qenex.id,
  ]

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  custom_data = base64encode(<<-EOF
    #!/bin/bash
    curl -fsSL https://qenex.ai/install.sh | sudo bash
    systemctl start qenex-os
  EOF
  )
}

# Outputs
output "public_ip" {
  value = azurerm_public_ip.qenex.ip_address
}