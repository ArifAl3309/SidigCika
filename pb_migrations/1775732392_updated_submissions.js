/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // update collection data
  unmarshal({
    "deleteRule": "@request.auth.role = 'teacher' || @request.auth.role = 'admin'",
    "listRule": "@request.auth.id != '' && (@request.auth.id = user_id || @request.auth.role = 'teacher' || @request.auth.role = 'admin')",
    "updateRule": "@request.auth.role = 'admin'",
    "viewRule": "@request.auth.id = user_id || @request.auth.role = 'teacher' || @request.auth.role = 'admin'"
  }, collection)

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // update collection data
  unmarshal({
    "deleteRule": "",
    "listRule": "",
    "updateRule": "",
    "viewRule": ""
  }, collection)

  return app.save(collection)
})
