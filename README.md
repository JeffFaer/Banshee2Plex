# Banshee2Plex

Based on [Banshee2Clementine](https://github.com/slaanesh/Banshee2Clementine).
This project copies ratings from [Banshee](http://banshee.fm) to [Plex](https://plex.tv).

Example usage:
```shell
$ sudo systemctl stop plexmediaserver.service
$ cp "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db" ~
$ cp "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db" ~/plex.backup.db
$ ./b2p.py --plex-account foo@bar.email --update-ratings --plex-db ~/com.plexapp.plugins.library.db
$ sudo mv ~/com.plexapp.plugins.library.db "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases"
$ sudo systemctl start plexmediaserver.service
```

If something went wrong, restore plex's DB with the backup:
```shell
$ sudo systemctl stop plexmediaserver.service
$ sudo cp ~/plex.backup.db "/var/lib/plexmediaserver/Library/Application Support/Plex Media Server/Plug-in Support/Databases/com.plexapp.plugins.library.db"
$ sudo systemctl start plexmediaserver.service
```
