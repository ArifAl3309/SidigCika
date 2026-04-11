/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // add field
  collection.fields.addAt(9, new Field({
    "hidden": false,
    "id": "autodateb242c3fdb7",
    "name": "created",
    "onCreate": true,
    "onUpdate": false,
    "presentable": false,
    "system": false,
    "type": "autodate"
  }))

  // add field
  collection.fields.addAt(10, new Field({
    "hidden": false,
    "id": "autodate49801807b7",
    "name": "updated",
    "onCreate": true,
    "onUpdate": true,
    "presentable": false,
    "system": false,
    "type": "autodate"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_3482339971")

  // remove field
  collection.fields.removeById("autodateb242c3fdb7")

  // remove field
  collection.fields.removeById("autodate49801807b7")

  return app.save(collection)
})
