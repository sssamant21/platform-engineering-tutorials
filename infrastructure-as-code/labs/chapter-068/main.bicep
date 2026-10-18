targetScope = 'resourceGroup'

@description('Deployment environment')
@allowed(['lab', 'dev'])
param environment string = 'lab'

@description('Azure region of the resource group')
param location string = resourceGroup().location

@description('Unique, globally available storage account name')
@minLength(3)
@maxLength(24)
param storageAccountName string

module storage './modules/storage.bicep' = {
  name: 'chapter068-storage'
  params: {
    location: location
    storageAccountName: storageAccountName
  }
}

output environmentName string = environment
output storageResourceId string = storage.outputs.storageResourceId
