var clientRecord = Ext.data.Record.create([{
    name: 'name'
}, {
    name: 'ip'
}, {
    name: 'group'
}, {
    name: 'status'
}, {
    name: 'msg'
}]);

var clientStore = new Ext.data.Store({
    reader: new Ext.data.JsonReader({
        id: 'id'
    }, clientRecord),
});

var groupStore = new Ext.data.GroupingStore({
    reader: new Ext.data.JsonReader({
        id: 'id'
    }, clientRecord),
	groupField: 'group',
});

Ext.onReady(function() {
    var clientView = new Ext.DataView({
        cls: 'client-view',
        tpl: '<tpl for=".">' +
        		'<tpl if="status == \'Conectado\'">' +
        			'<div class="client_source"><img class="icon_client" src="resources/images/default/s.gif"/>{name}</div>' +
        		'</tpl>' +
        		'<tpl if="status != \'Conectado\'">' +
        			'<div class="client_source client_disconnected"><img class="icon_client" src="resources/images/default/s.gif"/>{name}</div>' +
        		'</tpl>' +
        	 '</tpl>',
    	itemSelector: "div.client_source",
    	selectedClass: "client_selected",
    	overClass: "client_over",   
    	singleSelect: false,
    	multiSelect: true,
        store: clientStore,
        listeners: {
    		contextmenu: onClientContextMenu,
            render: initializeClientDragZone,
        },
    });
    
    var groupGrid = new Ext.grid.GridPanel({
        title: 'Grupos',
        region: 'center',
        margins: '0 5 5 0',
        columns: [{
            dataIndex: 'name',
            header: 'Nombre',
            width: 50
        }, {
            dataIndex: 'ip',
            header: 'Direccion IP',
            width: 50
        }, {
            dataIndex: 'group',
            header: 'Grupo',
            width: 50,
            hidden: true,
            hiddeable: false,
        }, {
            dataIndex: 'status',
            header: 'Estado',
            width: 50
        }, {
            dataIndex: 'msg',
            header: 'Mensaje',
            width: 200,
        }],
        view: new Ext.grid.GroupingView({
            forceFit:true,
            groupTextTpl: '{text} ({[values.rs.length]} {[values.rs.length > 1 ? "Miembros" : "Miembro"]})'
        }),
        store: groupStore,
        listeners: {
            render: initializeClientDropZone,
    		rowcontextmenu: onGroupRowContextMenu,
        },
	    iconCls: 'icon-grid',
	    cls: 'group-member'
    });
    

    
    new Ext.Viewport({
        layout: 'border',
        items: [{
            cls: 'app-header',
            layout: 'fit',
            region: 'north',
            html: '<div class="div_banner"><img class="logo_left" src="media/banner_left.png" /><img class="logo_right" src="media/banner_right.png" /></div>',
            margins: '5 5 5 5'
        }, {
            title: 'Clientes',
            region: 'west',
            width: 200,
            margins: '0 5 5 5',
            items: clientView
        }, groupGrid ]
    });

    startStomp();
});

var start = new Ext.util.DelayedTask(function(){
	startStomp();
})

function processData(data){
    clients = [];
    groups = [];
    for (i=0; i < data.length; i++) {
		recordg = groupStore.getById(data[i].id);
		recordc = clientStore.getById(data[i].id);
    	if ( data[i].group == null ) {
    		if ( recordg != undefined )
    			groupStore.remove(recordg);
    		if ( recordc == undefined )
    			clients.push(data[i]);
    		else {
    			recordc.data['status'] = data[i].status;
    			recordc.data['msg'] = data[i].msg;
    			recordc.commit();
    		}
    	}
    	else {
    		if ( recordc != undefined )
    			clientStore.remove(recordc);
    		if ( recordg == undefined )
    			groups.push(data[i]);
    		else {
    			recordg.data['status'] = data[i].status;
    			recordg.data['msg'] = data[i].msg;
    			recordg.commit();
    		}
    	}
    }
    clientStore.loadData(clients,true);
    groupStore.loadData(groups,true);	
}

function startStomp(){
    stomp = new STOMPClient();
    stomp.onopen = function() {
    	Ext.get(Ext.query("body")).setStyle("opacity", "1");
        Ext.Ajax.request({
            url: 'control/json_status',
            success: function(r) {
                data = Ext.util.JSON.decode(r.responseText);
                processData(data);
            }
        });
    };
    stomp.onclose = function(c) {
    	Ext.get(Ext.query("body")).setStyle("opacity", "0.2");
    	start.delay(2000);
    };
    stomp.onerror = function(error) {
        alert("Error: " + error);
    };
    stomp.onerrorframe = function(frame) {
        alert("Error: " + frame.body);
    };
    stomp.onconnectedframe = function() {
        stomp.subscribe("/livemonitor");
    };
    stomp.onmessageframe = function(frame) {            
        // Recogemos el objeto JSON en una variable
        data = Ext.util.JSON.decode(frame.body);
        // Cargamos el objeto en los stores
        processData(data);
    };
    stomp.connect('localhost', 61613);
}

function onClientContextMenu(view, index, item, e) {
	if (!this.contextMenu) {
		this.contextMenu = new Ext.menu.Menu({
		id: 'gridCtxMenu',
		items: [{
				scope: this,
				text: 'Reiniciar',
				handler: function(b, e) {
		            hosts = [];
		            for (i = 0; i < this.clientRecords.length; i++)
		            	hosts[i] = this.clientRecords[i].data['ip'];
		            Ext.Ajax.request({
		            	url: 'control/reboot',
		            	params: { 'hosts': hosts },
		            });
				}
			},{
				scope: this,
				text: 'Controlar Remotamente',
				handler: function(b, e) {
					for (i = 0; i < this.clientRecords.length; i++)
						window.open('backharddi-ng://' + this.clientRecords[i].data['ip']);
				}
		}]
		});
	}
    var sourceEl = e.getTarget();
    if (sourceEl) {
    	var records = view.getSelectedRecords();  
    	var clicked = view.getRecord( sourceEl );  
    	if( records.indexOf( clicked ) == -1 ) {  
    	    records.push(clicked);  
    	}
    	this.clientRecords = records;
    }
	e.stopEvent();
	var xy = e.getXY();
	this.contextMenu.showAt(xy);
}

function onGroupRowContextMenu(g, rowIndex, e) {
	if (!this.contextMenu) {
		this.contextMenu = new Ext.menu.Menu({
		id: 'gridCtxMenu',
		items: [{
			scope: this,
			text: 'Reiniciar',
			handler: function(b, e) {
	            hosts = [];
	            for (i = 0; i < this.clientRecords.length; i++)
	            	hosts[i] = this.clientRecords[i].data['ip'];
	            Ext.Ajax.request({
	            	url: 'control/reboot',
	            	params: { 'hosts': hosts },
	            });
			}
		},{
			scope: this,
			text: 'Controlar Remotamente',
			handler: function(b, e) {
				for (i = 0; i < this.clientRecords.length; i++)
					window.open('backharddi-ng://' + this.clientRecords[i].data['ip']);
			}
		},{
			scope: this,
			text: 'Quitar del grupo',
			handler: function(b, e) {
	            hosts = [];
	            for (i = 0; i < this.clientRecords.length; i++)
	            	hosts[i] = this.clientRecords[i].data['ip'];
				Ext.Ajax.request({
					url: 'control/del_from_group',
					params: { 'name': this.group, 'hosts': hosts },
				});
			}
		},{
			scope: this,
			text: 'Lanzar Grupo',
			handler: function(b, e) {
				Ext.Ajax.request({
					url: 'control/group_launch',
					params: { 'name': this.group },
				});
			}
		}]
		});
	}
	this.group = groupStore.getAt(rowIndex).data['group'];
	records = g.getSelectionModel().getSelections();
	clicked = groupStore.getAt(rowIndex);
	if( records.indexOf( clicked ) == -1 ) {  
	    records.push(clicked);  
	}
	this.clientRecords = records;
	e.stopEvent();
	var xy = e.getXY();
	this.contextMenu.showAt(xy);
}

function initializeClientDragZone(v) {
    v.dragZone = new Ext.dd.DragZone(v.getEl(), {

        getDragData: function(e) {
            var sourceEl = e.getTarget(v.itemSelector, 10);
            if (sourceEl) {
            	var records = v.getSelectedRecords();  
            	var clicked = v.getRecord( sourceEl );  
            	if( records.indexOf( clicked ) == -1 ) {  
            	    records.push(clicked);  
            	}  
            	d = sourceEl.cloneNode(true);  
            	if( records.length > 1)   
            	    Ext.DomHelper.overwrite(d, {html: records.length + ' clientes seleccionados'});  
                d.id = Ext.id();
                return v.dragData = {
                    sourceEl: sourceEl,
                    clientRecords: records,
                    repairXY: Ext.fly(sourceEl).getXY(),
                    ddel: d,
                }
            }
        },

        getRepairXY: function() {
            return this.dragData.repairXY;
        }
    });
}

function onClickImageNode(node, e) {
	n = node;
	value = '';
	while (n.parentNode) {
		if (value)
			value = n.text + '/' + value;
		else
			value = n.text;
		n = n.parentNode;
	}
	imagenTextField.setValue(value);
}

imagenTextField = new Ext.form.TextField({name: 'backup', fieldLabel: 'Imagen', allowBlank: false});

function initializeClientDropZone(g) {
    g.dropZone = new Ext.dd.DropZone(g.getView().scroller, {
        getTargetFromEvent: function(e) {
            return e.getTarget('.group-member');
        },
        onNodeEnter : function(target, dd, e, data){ 
            Ext.fly(target).addClass('group-target-hover');
        },
        onNodeOut : function(target, dd, e, data){ 
            Ext.fly(target).removeClass('group-target-hover');
        },
        onNodeDrop : function(target, dd, e, data){
        	if (data.clientRecords.length == 1)
        		modoitems = [{boxLabel: 'Generar', name: 'modo', inputValue: 'gen'},
        					 {boxLabel: 'Restaurar', name: 'modo', inputValue: 'rest', checked: true}];
        	else
        		modoitems = [{boxLabel: 'Restaurar', name: 'modo', inputValue: 'rest', checked: true}];
        	configGroupForm = new Ext.FormPanel({ 
        	    labelWidth:80,
        	    url:'control/group_config', 
        	    frame:true,
        	    defaultType:'textfield',
        	    monitorValid:true,
        	    items:[{ 
        		        fieldLabel:'Nombre del Grupo',
        		        name:'name',
        		        allowBlank:false,
        		        value: 'Grupo ' + (groupStore.getTotalCount() + 1),
        	    	},{ 
        	    		xtype: 'radiogroup',
        		        fieldLabel: 'Modo',
        		        items: modoitems,
        	        },imagenTextField
        	        ,{
    	            	name:'imagenes',
    	            	xtype:'treepanel',
    	            	fieldLabel:'Imagenes Disponibles',
    	            	height:180,
    	            	autoScroll:true,
    	            	border:true,
    	            	bodyStyle:'background-color:white;border:1px solid #B5B8C8',
    	            	rootVisible:false,
    	            	dataUrl: 'control/tree',
    	            	root:{
    	            	 nodeType:'async',
    	            	 text:'root',
    	            	 id:'root',
    	            	 expanded:true,
    	            	},
    	            	listeners: { click: onClickImageNode }
        	        },{ 
        	        	xtype: 'checkbox',
        	            boxLabel:'Reiniciar todos los miembros del grupo al terminar el proceso', 
        	            name:'reboot', 
        	        },{ 
        	        	xtype: 'checkbox',
        	            boxLabel:'Lanzar grupo inmediatamente', 
        	            name:'launch', 
        	        }],
        	    buttons:[{ 
        	            text:'Ok',
        	            formBind: true,
        	            handler:function(){ 
        	                configGroupForm.getForm().submit({ 
        	                    method:'POST', 
        	                    success:function(){
        	                		configGroupForm.getForm().reset();
        	                		configGroupForm.configWin.hide();
        	                    },
        	                    failure:function(form, action){ 
        	                        Ext.Msg.alert('Error al configurar el grupo!'); 
        	                        configGroupForm.getForm().reset(); 
        	                    },
        	                    params: { hosts: [configGroupForm.hosts] },
        	                }); 
        	            } 
        	        }] 
        	});
            configWin = new Ext.Window({
            	title		: 'Configuración del Grupo',
                modal       : true,
                resizable   : false,
                center      : true,
                layout:'fit',
                width:500,
                height:400,
                closeAction:'hide',
                items: [configGroupForm],
            });
            configGroupForm.configWin = configWin;
            hosts = [];
            for (i = 0; i < data.clientRecords.length; i++)
            	hosts[i] = data.clientRecords[i].data['ip'];
            configGroupForm.hosts = hosts;
            configWin.show();
            return true;
        }
    });
}
