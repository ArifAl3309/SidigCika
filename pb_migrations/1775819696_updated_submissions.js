/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // update collection data
  unmarshal({
    "updateRule": "@request.auth.role = 'teacher' || @request.auth.role = 'admin'"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // update collection data
  unmarshal({
    "updateRule": "@request.auth.role = 'admin'"
  }, collection)

  return app.save(collection)
})
