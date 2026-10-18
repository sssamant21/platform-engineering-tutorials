targetScope = 'subscription'

@allowed(['lab', 'dev'])
param environment string = 'lab'

param resourceGroupName string
param location string = deployment().location
@minLength(3)
@maxLength(24)
param storageAccountName string

resource targetRg 'Microsoft.Resources/resourceGroups@2022-09-01' existing = {
  name: resourceGroupName
}

module storage './modules/private-storage.bicep' = {
  name: 'chapter070-private-storage'
  scope: targetRg
  params: {
    location: location
    storageAccountName: storageAccountName
  }
}

output environmentName string = environment
output storageResourceId string = storage.outputs.storageResourceId
