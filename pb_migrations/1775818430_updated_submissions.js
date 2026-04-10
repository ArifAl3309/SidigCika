/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // update field
  collection.fields.addAt(7, new Field({
    "hidden": false,
    "id": "number848901969",
    "max": null,
    "min": 0,
    "name": "score",
    "onlyInt": false,
    "presentable": false,
    "required": false,
    "system": false,
    "type": "number"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // update field
  collection.fields.addAt(7, new Field({
    "hidden": false,
    "id": "number848901969",
    "max": null,
    "min": 0,
    "name": "score",
    "onlyInt": false,
    "presentable": false,
    "required": true,
    "system": false,
    "type": "number"
  }))

  return app.save(collection)
})
