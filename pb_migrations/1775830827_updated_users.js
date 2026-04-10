/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // remove field
  collection.fields.removeById("text3491757652")

  // add field
  collection.fields.addAt(11, new Field({
    "hidden": false,
    "id": "select299815248",
    "maxSelect": 1,
    "name": "Kelas",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "select",
    "values": [
      "XI.1",
      "XI.2",
      "XI.3"
    ]
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("_pb_users_auth_")

  // add field
  collection.fields.addAt(11, new Field({
    "autogeneratePattern": "",
    "hidden": false,
    "id": "text3491757652",
    "max": 0,
    "min": 0,
    "name": "kelas",
    "pattern": "",
    "presentable": false,
    "primaryKey": false,
    "required": false,
    "system": false,
    "type": "text"
  }))

  // remove field
  collection.fields.removeById("select299815248")

  return app.save(collection)
})
