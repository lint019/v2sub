// import Vue from 'vue'
// import App from './App.vue'
// import router from './router/index'
// import store from './store/index'

// import 'vuetify/dist/vuetify.min.css'

// Vue.config.productionTip = false


// vuetify 自定义配置
// export default new Vuetify({})

var main = (function (Vue, extendAM) {
    var main = {};
    main.vm = null;

    main.appData = {
        date: null,
        percent:50,
        services:5,
        availableds:6,
        offers:7,
        urls:[
               "https://www.youtube.com",
               "https://www.twitter.com",
               "https://www.gettr.com",
            ],
        bars: [
            { class: '' },
            { class: '', dark: true },
            { class: 'primary', dark: true },
            { class: 'elevation-0' },
          ],
        trip: {
            name: '',
            location: null,
            start: null,
            end: null,
        },
        drawer: null,
        items: [
          { title: 'https://www.youtube.com', icon: 'mdi-view-dashboard' },
          { title: 'https://www.twitter.com', icon: 'mdi-forum' },
          { title: 'https://www.gettr.com', icon: 'mdi-forum' },
          { title: 'https://www.github.com', icon: 'mdi-forum' },
        ],
        selected_url:null,
        locations: ['Australia', 'Barbados', 'Chile', 'Denmark', 'Ecuador', 'France'],
        position: 'bottom right',
        theme: 'error',
        open: false,

        /////////////////////////////////////////////
        headPath: 'http://localhost:5000/',
        videoList: [],
        videoListCopy: [],
        showModal: false,
        modalType: 'addTask',
        // tablist: ['status', 'details', 'file24s', 'peers', 'options'],
        tablist: ['Status', 'Details', 'Log'],
        showTab: 'Status',
        stateCounter: { all: 0, downloading: 0, finished: 0, paused: 0, invalid: 0,progress:0},
        modalData: {
            add: { url: '', ydl_opts: {} },
            remove: { removeFile: false },
            preference: {v2ray: {format: '', proxy: '', ratelimit: '', outtmpl: ''}, general: {download_dir: '', db_path: '', log_size: ''}},
        },
        currentSelected: null,
        taskDetails: {
            'thumbnail':''
        },
        dialog: false,
        taskInfoUrl: null,
        toast:{
            multiLine: true,
            snackbar: false,
            text: `I'm a multi-line snackbar.`,
          },

        status: 'all',

    };
    main.createVm = function (res) {
        var that = main;
        that.vm = new Vue({
            el: '#app',
            vuetify: new Vuetify(),
            data: that.appData,

            watch: {
                currentSelected () {
                  this.drawer = false
                },
                selected_url () {
                  this.drawer = false
                },
              },
            mounted: function () {
                setInterval(main.timeOut, 3000);
            },
            methods: {
                selected: function(index){
                    var _self = this;
                    this.currentSelected = index;
                    _self.taskInfoUrl = _self.headPath + 'task/tid/' +  (_self.videoList[_self.currentSelected] && _self.videoList[_self.currentSelected].tid) + '/status';
                    _self.getTaskInfoById();
                },
                getTaskInfoById: function(){
                    var _self = this;
                    if(!_self.taskInfoUrl) return false;
                    Vue.http.get(_self.taskInfoUrl).then(function(res){
                        var responseJSON = res.data;
                        if(responseJSON.status === 'error'){
                            return false;
                        }
                        _self.taskDetails = responseJSON.detail;
                    }, function(err){
                        _self.showAlertToast('Network connection lost', 'error');
                    });
                },
                filterTasks: function(filterStatus) {
                    var _self = this;
                    _self.drawer =null;
                    _self.status = filterStatus;
                    that.getTaskList();
                },
                startAll: function () {
                    var _self = this;
                    var url = _self.headPath + 'start_all';
                    Vue.http.post(url, _self.modalData.preference, {emulateJSON: false}).then(function(res){
                        console.log("Successfully");
                    }, function(err){
                        _self.showAlertToast(err, 'error');
                    });
                    _self.showModal = false;
                },
                subscribe: function () {
                    var _self = this;
                    var url = _self.headPath + 'subscribe';
                    Vue.http.post(url, _self.modalData.preference, {emulateJSON: false}).then(function(res){
                        console.log("Successfully");
                    }, function(err){
                        _self.showAlertToast(err, 'error');
                    });
                    _self.showModal = false;
                },
                offer: function () {
                    var _self = this;
                    var url = _self.headPath + 'offer';
                    Vue.http.post(url, _self.modalData.preference, {emulateJSON: false}).then(function(res){
                        console.log("Successfully");
                    }, function(err){
                        _self.showAlertToast(err, 'error');
                    });
                    _self.showModal = false;
                },
                preference: function() {
                    var _self = this;
                    var url = _self.headPath + 'config';

                    this.showModal = true;
                    this.modalType = 'updatePreference';
                    Vue.http.get(url).then(function(res) {
                        var responseJSON = res.data;
                        // var responseJSON = JSON.parse(res.data);
                        if (responseJSON.status === 'error') {
                            return false;
                        } else {
                            config = responseJSON['config'];
                            _self.modalData.preference.general.download_dir = config.general.download_dir;
                            _self.modalData.preference.general.db_path = config.general.db_path;
                            _self.modalData.preference.general.log_size = config.general.log_size;
                            _self.modalData.preference.v2ray.format = config.v2ray.format;
                            _self.modalData.preference.v2ray.proxy = config.v2ray.proxy;
                            _self.modalData.preference.v2ray.ratelimit = config.v2ray.ratelimit;
                            _self.modalData.preference.v2ray.outtmpl = config.v2ray.outtmpl;
                        }
                    });
                },
                updatePreference: function () {
                    var _self = this;
                    var url = _self.headPath + 'config';
                    Vue.http.post(url, _self.modalData.preference, {emulateJSON: false}).then(function(res){
                        console.log("Successfully");
                    }, function(err){
                        _self.showAlertToast(err, 'error');
                    });
                    _self.showModal = false;
                },
                reboot: function(){
                    var _self = this;
                    var url = _self.headPath + 'reboot'                    
                    Vue.http.post(url, _self.modalData.preference, {emulateJSON: false}).then(function(res){
                        console.log("Successfully");
                    }, function(err){
                        _self.showAlertToast(err, 'error');
                    });
                    _self.showModal = false;
                },

                showConfigDialog:function(show){
                    var _self = this;
                    if(show){
                        _self.preference();
                    }
                    _self.dialog = show
                },
                showAlertToast(msg, theme) {
                    var _self = this;
                    _self.toast.text = msg
                    _self.toast.snackbar = true

                    
                }
            }
        })
    };

    main.getTaskList = function() {
        var that = main;
        var url = that.appData.headPath + 'task/list';
        url = url + '?state=' + that.appData.status;
        Vue.http.get(url).then(function(res){
            // var resData = JSON.parse(res.body);
            var resData = res.body;
            that.appData.videoList = resData.detail;
            that.appData.stateCounter = resData.state_counter;
            that.appData.stateCounter.all = that.appData.stateCounter.downloading +
                                              that.appData.stateCounter.finished +
                                              that.appData.stateCounter.paused +
                                              that.appData.stateCounter.invalid;
        }, function(err){
            that.vm.showAlertToast('Network connection lost', 'error');
        });
    };

    main.timeOut = function () {
        var that = main;
        that.getTaskList();
        console.log("timeout")

    };
    main.init = function () {
        var that = this;
        that.appData.headPath = window.location.protocol + '//' + window.location.host + '/';
        that.createVm();
    }
    return main;
})(Vue, {});
main.init();