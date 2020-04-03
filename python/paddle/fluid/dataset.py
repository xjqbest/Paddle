#   Copyright (c) 2018 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This is definition of dataset class, which is high performance IO."""

from paddle.fluid.proto import data_feed_pb2
from google.protobuf import text_format
from . import core
__all__ = ['DatasetFactory', 'InMemoryDataset', 'QueueDataset']


class DatasetFactory(object):
    """
    DatasetFactory is a factory which create dataset by its name,
    you can create "QueueDataset" or "InMemoryDataset", or "FileInstantDataset",
    the default is "QueueDataset".

    Example:
        .. code-block:: python

          import paddle.fluid as fluid
          dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")

    """

    def __init__(self):
        """ Init. """
        pass

    def create_dataset(self, datafeed_class="QueueDataset"):
        """
        Create "QueueDataset" or "InMemoryDataset", or "FileInstantDataset",
        the default is "QueueDataset".

        Args:
            datafeed_class(str): datafeed class name, QueueDataset or InMemoryDataset.
                                 Default is QueueDataset.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()

        """
        try:
            dataset = globals()[datafeed_class]()
            return dataset
        except:
            raise ValueError("datafeed class %s does not exist" %
                             datafeed_class)


class DatasetBase(object):
    """ Base dataset class. """

    def __init__(self):
        """ Init. """
        # define class name here
        # to decide whether we need create in memory instance
        self.proto_desc = data_feed_pb2.DataFeedDesc()
        self.proto_desc.pipe_command = "cat"
        self.dataset = core.Dataset("MultiSlotDataset")
        self.thread_num = 1
        self.filelist = []

    def set_pipe_command(self, pipe_command):
        """
        Set pipe command of current dataset
        A pipe command is a UNIX pipeline command that can be used only

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
              dataset.set_pipe_command("python my_script.py")

        Args:
            pipe_command(str): pipe command

        """
        self.proto_desc.pipe_command = pipe_command

    def set_fea_eval(self, record_candidate_size, fea_eval=True):
        """
        set fea eval mode for slots shuffle to debug the importance level of
        slots(features), fea_eval need to be set True for slots shuffle.
        
        Args:
            record_candidate_size(int): size of instances candidate to shuffle 
                                        one slot
            fea_eval(bool): whether enable fea eval mode to enable slots shuffle.
                            default is True.
            
        Examples:
            .. code-block:: python

            import paddle.fluid as fluid
            dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
            dataset.set_fea_eval(1000000, True)

        """
        if fea_eval:
            self.dataset.set_fea_eval(fea_eval, record_candidate_size)
        self.fea_eval = fea_eval

    def slots_shuffle(self, slots):
        """
        Slots Shuffle 
        Slots Shuffle is a shuffle method in slots level, which is usually used 
        in sparse feature with large scale of instances. To compare the metric, i.e.
        auc while doing slots shuffle on one or several slots with baseline to 
        evaluate the importance level of slots(features).
        
        Args:
            slots(list[string]): the set of slots(string) to do slots shuffle.

        Examples:
            import paddle.fluid as fluid
            dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
            dataset.set_merge_by_lineid()
            #suppose there is a slot 0
            dataset.slots_shuffle(['0'])
        """
        if self.fea_eval:
            slots_set = set(slots)
            self.dataset.slots_shuffle(slots_set)

    def set_batch_size(self, batch_size):
        """
        Set batch size. Will be effective during training

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
              dataset.set_batch_size(128)

        Args:
            batch_size(int): batch size

        """
        self.proto_desc.batch_size = batch_size

    def set_thread(self, thread_num):
        """
        Set thread num, it is the num of readers.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
               dataset.set_thread(12)

        Args:
            thread_num(int): thread num
        """
        self.dataset.set_thread_num(thread_num)
        self.thread_num = thread_num

    def set_filelist(self, filelist):
        """
        Set file list in current worker.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
              dataset.set_filelist(['a.txt', 'b.txt'])

        Args:
            filelist(list): file list
        """
        self.dataset.set_filelist(filelist)
        self.filelist = filelist

    def set_use_var(self, var_list):
        """
        Set Variables which you will use.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
              dataset.set_use_var([data, label])

        Args:
            var_list(list): variable list
        """
        multi_slot = self.proto_desc.multi_slot_desc
        for var in var_list:
            slot_var = multi_slot.slots.add()
            slot_var.is_used = True
            slot_var.name = var.name
            if var.lod_level == 0:
                slot_var.is_dense = True
                slot_var.shape.extend(var.shape)
            if var.dtype == core.VarDesc.VarType.FP32:
                slot_var.type = "float"
            elif var.dtype == core.VarDesc.VarType.INT64:
                slot_var.type = "uint64"
            else:
                raise ValueError(
                    "Currently, fluid.dataset only supports dtype=float32 and dtype=int64"
                )

    def set_hdfs_config(self, fs_name, fs_ugi):
        """
        Set hdfs config: fs name ad ugi

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
              dataset.set_hdfs_config("my_fs_name", "my_fs_ugi")

        Args:
            fs_name(str): fs name
            fs_ugi(str): fs ugi
        """
        self.dataset.set_hdfs_config(fs_name, fs_ugi)

    def set_download_cmd(self, download_cmd):
        """
        Set customized download cmd: download_cmd

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
              dataset.set_download_cmd("./read_from_afs")

        Args:
            download_cmd(str): customized download command
        """
        self.dataset.set_download_cmd(download_cmd)

    def _prepare_to_run(self):
        """
        Set data_feed_desc before load or shuffle,
        user no need to call this function.
        """
        if self.thread_num > len(self.filelist):
            self.thread_num = len(self.filelist)
        self.dataset.set_thread_num(self.thread_num)
        self.dataset.set_data_feed_desc(self.desc())
        self.dataset.create_readers()

    def _finish_to_run(self):
        self.dataset.destroy_readers()

    def desc(self):
        """
        Returns a protobuf message for this DataFeedDesc

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset()
              print(dataset.desc())

        Returns:
            A string message
        """
        return text_format.MessageToString(self.proto_desc)

    def _dynamic_adjust_before_train(self, thread_num):
        pass

    def _dynamic_adjust_after_train(self):
        pass


class InMemoryDataset(DatasetBase):
    """
    InMemoryDataset, it will load data into memory
    and shuffle data before training.
    This class should be created by DatasetFactory

    Example:
        dataset = paddle.fluid.DatasetFactory().create_dataset("InMemoryDataset")
    """

    def __init__(self):
        """ Init. """
        super(InMemoryDataset, self).__init__()
        self.proto_desc.name = "MultiSlotInMemoryDataFeed"
        self.fleet_send_batch_size = None
        self.is_user_set_queue_num = False
        self.queue_num = None
        self.parse_ins_id = False
        self.parse_content = False
        self.merge_by_lineid = False
        self.fleet_send_sleep_seconds = None

    def _prepare_to_run(self):
        """
        Set data_feed_desc before load or shuffle,
        user no need to call this function.
        """
        if self.thread_num <= 0:
            self.thread_num = 1
        self.dataset.set_thread_num(self.thread_num)
        if self.queue_num is None:
            self.queue_num = self.thread_num
        self.dataset.set_queue_num(self.queue_num)
        self.dataset.set_parse_ins_id(self.parse_ins_id)
        self.dataset.set_parse_content(self.parse_content)
        self.dataset.set_data_feed_desc(self.desc())
        self.dataset.create_channel()
        self.dataset.create_readers()

    def _dynamic_adjust_before_train(self, thread_num):
        if not self.is_user_set_queue_num:
            self.dataset.dynamic_adjust_channel_num(thread_num, False)
        self.dataset.dynamic_adjust_readers_num(thread_num)

    def _dynamic_adjust_after_train(self):
        if not self.is_user_set_queue_num:
            self.dataset.dynamic_adjust_channel_num(self.thread_num, False)
        self.dataset.dynamic_adjust_readers_num(self.thread_num)

    def set_queue_num(self, queue_num):
        """
        Set Dataset output queue num, training threads get data from queues

        Args:
            queue_num(int): dataset output queue num

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              dataset.set_queue_num(12)

        """
        self.is_user_set_queue_num = True
        self.queue_num = queue_num

    def set_parse_ins_id(self, parse_ins_id):
        """
        Set id Dataset need to parse insid

        Args:
            parse_ins_id(bool): if parse ins_id or not

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              dataset.set_parse_ins_id(True)

        """
        self.parse_ins_id = parse_ins_id

    def set_parse_content(self, parse_content):
        """
        Set if Dataset need to parse content

        Args:
            parse_content(bool): if parse content or not

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              dataset.set_parse_content(True)

        """
        self.parse_content = parse_content

    def set_fleet_send_batch_size(self, fleet_send_batch_size=1024):
        """
        Set fleet send batch size, default is 1024

        Args:
            fleet_send_batch_size(int): fleet send batch size

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              dataset.set_fleet_send_batch_size(800)

        """
        self.fleet_send_batch_size = fleet_send_batch_size

    def set_fleet_send_sleep_seconds(self, fleet_send_sleep_seconds=0):
        """
        Set fleet send sleep time, default is 0

        Args:
            fleet_send_sleep_seconds(int): fleet send sleep time

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              dataset.set_fleet_send_sleep_seconds(2)

        """
        self.fleet_send_sleep_seconds = fleet_send_sleep_seconds

    def set_merge_by_lineid(self, merge_size=2):
        """
        Set merge by line id, instances of same line id will be merged after
        shuffle, you should parse line id in data generator.

        Args:
            merge_size(int): ins size to merge. default is 2.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              dataset.set_merge_by_lineid()

        """
        self.dataset.set_merge_by_lineid(merge_size)
        self.merge_by_lineid = True
        self.parse_ins_id = True

    def set_generate_unique_feasigns(self, generate_uni_feasigns, shard_num):
        self.dataset.set_generate_unique_feasigns(generate_uni_feasigns)
        self.gen_uni_feasigns = generate_uni_feasigns
        self.local_shard_num = shard_num

    def generate_local_tables_unlock(self, table_id, fea_dim, read_thread_num,
                                     consume_thread_num, shard_num):
        self.dataset.generate_local_tables_unlock(
            table_id, fea_dim, read_thread_num, consume_thread_num, shard_num)

    def load_into_memory(self):
        """
        Load data into memory

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.load_into_memory()
        """
        self._prepare_to_run()
        self.dataset.load_into_memory()

    def preload_into_memory(self, thread_num=None):
        """
        Load data into memory in async mode

        Args:
            thread_num(int): preload thread num

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.preload_into_memory()
              dataset.wait_preload_done()
        """
        self._prepare_to_run()
        if thread_num is None:
            thread_num = self.thread_num
        self.dataset.set_preload_thread_num(thread_num)
        self.dataset.create_preload_readers()
        self.dataset.preload_into_memory()

    def wait_preload_done(self):
        """
        Wait preload_into_memory done

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.preload_into_memory()
              dataset.wait_preload_done()
        """
        self.dataset.wait_preload_done()
        self.dataset.destroy_preload_readers()

    def local_shuffle(self):
        """
        Local shuffle

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.load_into_memory()
              dataset.local_shuffle()
        """
        self.dataset.local_shuffle()

    def global_shuffle(self, fleet=None, thread_num=12):
        """
        Global shuffle.
        Global shuffle can be used only in distributed mode. i.e. multiple
        processes on single machine or multiple machines training together.
        If you run in distributed mode, you should pass fleet instead of None.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              from paddle.fluid.incubate.fleet.parameter_server.pslib import fleet
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.load_into_memory()
              dataset.global_shuffle(fleet)

        Args:
            fleet(Fleet): fleet singleton. Default None.
            thread_num(int): shuffle thread num. Default is 12.

        """
        trainer_num = 1
        if fleet is not None:
            fleet._role_maker.barrier_worker()
            trainer_num = fleet.worker_num()
        if self.fleet_send_batch_size is None:
            self.fleet_send_batch_size = 1024
        if self.fleet_send_sleep_seconds is None:
            self.fleet_send_sleep_seconds = 0
        self.dataset.register_client2client_msg_handler()
        self.dataset.set_trainer_num(trainer_num)
        self.dataset.set_fleet_send_batch_size(self.fleet_send_batch_size)
        self.dataset.set_fleet_send_sleep_seconds(self.fleet_send_sleep_seconds)
        if fleet is not None:
            fleet._role_maker.barrier_worker()
        self.dataset.global_shuffle(thread_num)
        if fleet is not None:
            fleet._role_maker.barrier_worker()
        if self.merge_by_lineid:
            self.dataset.merge_by_lineid()
        if fleet is not None:
            fleet._role_maker.barrier_worker()

    def release_memory(self):
        """
        Release InMemoryDataset memory data, when data will not be used again.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              from paddle.fluid.incubate.fleet.parameter_server.pslib import fleet
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.load_into_memory()
              dataset.global_shuffle(fleet)
              exe = fluid.Executor(fluid.CPUPlace())
              exe.run(fluid.default_startup_program())
              exe.train_from_dataset(fluid.default_main_program(), dataset)
              dataset.release_memory()

        """
        self.dataset.release_memory()

    def get_memory_data_size(self, fleet=None):
        """
        Get memory data size, user can call this function to know the num
        of ins in all workers after load into memory.

        Note:
            This function may cause bad performance, because it has barrier

        Args:
            fleet(Fleet): Fleet Object.

        Returns:
            The size of memory data.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              from paddle.fluid.incubate.fleet.parameter_server.pslib import fleet
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.load_into_memory()
              print dataset.get_memory_data_size(fleet)

        """
        import numpy as np
        local_data_size = self.dataset.get_memory_data_size()
        local_data_size = np.array([local_data_size])
        if fleet is not None:
            global_data_size = local_data_size * 0
            fleet._role_maker.all_reduce_worker(local_data_size,
                                                global_data_size)
            return global_data_size[0]
        return local_data_size[0]

    def get_shuffle_data_size(self, fleet=None):
        """
        Get shuffle data size, user can call this function to know the num
        of ins in all workers after local/global shuffle.

        Note:
            This function may cause bad performance to local shuffle,
            because it has barrier. It does not affect global shuffle.

        Args:
            fleet(Fleet): Fleet Object.

        Returns:
            The size of shuffle data.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              from paddle.fluid.incubate.fleet.parameter_server.pslib import fleet
              dataset = fluid.DatasetFactory().create_dataset("InMemoryDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.load_into_memory()
              dataset.global_shuffle(fleet)
              print dataset.get_shuffle_data_size(fleet)

        """
        import numpy as np
        local_data_size = self.dataset.get_shuffle_data_size()
        local_data_size = np.array([local_data_size])
        if fleet is not None:
            global_data_size = local_data_size * 0
            fleet._role_maker.all_reduce_worker(local_data_size,
                                                global_data_size)
            return global_data_size[0]
        return local_data_size[0]


class QueueDataset(DatasetBase):
    """
    QueueDataset, it will process data streamly.

    Examples:
        .. code-block:: python

          import paddle.fluid as fluid
          dataset = fluid.DatasetFactory().create_dataset("QueueDataset")

    """

    def __init__(self):
        """
        Initialize QueueDataset
        This class should be created by DatasetFactory
        """
        super(QueueDataset, self).__init__()
        self.proto_desc.name = "MultiSlotDataFeed"
        self.parse_ins_id = False
        self.parse_content = False

    def _prepare_to_run(self):
        """
        Set data_feed_desc/thread num/filelist before run,
        user no need to call this function.
        """
        if self.thread_num > len(self.filelist):
            self.thread_num = len(self.filelist)
        if self.thread_num == 0:
            self.thread_num = 1
        self.dataset.set_thread_num(self.thread_num)
        self.dataset.set_filelist(self.filelist)
        self.dataset.set_data_feed_desc(self.desc())
        self.dataset.set_parse_ins_id(self.parse_ins_id)
        self.dataset.set_parse_content(self.parse_content)
        self.dataset.create_readers()

    def local_shuffle(self):
        """
        Local shuffle data.

        Local shuffle is not supported in QueueDataset
        NotImplementedError will be raised

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("QueueDataset")
              dataset.local_shuffle()

        Raises:
            NotImplementedError: QueueDataset does not support local shuffle

        """
        raise NotImplementedError(
            "QueueDataset does not support local shuffle, "
            "please use InMemoryDataset for local_shuffle")

    def global_shuffle(self, fleet=None):
        """
        Global shuffle data.

        Global shuffle is not supported in QueueDataset
        NotImplementedError will be raised

        Args:
            fleet(Fleet): fleet singleton. Default None.

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              from paddle.fluid.incubate.fleet.parameter_server.pslib import fleet
              dataset = fluid.DatasetFactory().create_dataset("QueueDataset")
              dataset.global_shuffle(fleet)

        Raises:
            NotImplementedError: QueueDataset does not support global shuffle

        """
        raise NotImplementedError(
            "QueueDataset does not support global shuffle, "
            "please use InMemoryDataset for global_shuffle")

    def set_parse_ins_id(self, parse_ins_id):
        self.parse_ins_id = parse_ins_id

    def set_parse_content(self, parse_content):
        self.parse_content = parse_content



class FileInstantDataset(DatasetBase):
    """
    FileInstantDataset, it will process data streamly.

    Examples:
        .. code-block:: python

          import paddle.fluid as fluid
          dataset = fluid.DatasetFactory.create_dataset("FileInstantDataset")
    """

    def __init__(self):
        """
        Initialize FileInstantDataset
        This class should be created by DatasetFactory
        """
        super(FileInstantDataset, self).__init__()
        self.proto_desc.name = "MultiSlotFileInstantDataFeed"

    def local_shuffle(self):
        """
        Local shuffle
        FileInstantDataset does not support local shuffle
        """
        raise NotImplementedError(
            "FileInstantDataset does not support local shuffle, "
            "please use InMemoryDataset for local_shuffle")

    def global_shuffle(self, fleet=None):
        """
        Global shuffle
        FileInstantDataset does not support global shuffle
        """
        raise NotImplementedError(
            "FileInstantDataset does not support global shuffle, "
            "please use InMemoryDataset for global_shuffle")


class BoxPSDataset(InMemoryDataset):
    """
    BoxPSDataset: derived from InMemoryDataset.

    Examples:
        .. code-block:: python

          import paddle.fluid as fluid
          dataset = fluid.DatasetFactory().create_dataset("BoxPSDataset")
    """

    def __init__(self):
        """
        Initialize BoxPSDataset
        This class should be created by DatasetFactory
        """
        super(BoxPSDataset, self).__init__()
        self.boxps = core.BoxPS(self.dataset)

    def set_date(self, date):
        """
        Workaround for date
        """
        year = int(date[:4])
        month = int(date[4:6])
        day = int(date[6:])
        self.boxps.set_date(year, month, day)

    def begin_pass(self):
        """
        Begin Pass
        Notify BoxPS to load sparse parameters of next pass to GPU Memory 

        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("BoxPSDataset")
              dataset.begin_pass()
        """
        self.boxps.begin_pass()

    def end_pass(self, need_save_delta):
        """
        End Pass
        Notify BoxPS that current pass ended 
        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("BoxPSDataset")
              dataset.end_pass(True)
        """
        self.boxps.end_pass(need_save_delta)

    def wait_preload_done(self):
        """
        Wait async preload done
        Wait Until Feed Pass Done
        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("BoxPSDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.preload_into_memory()
              dataset.wait_preload_done()
        """
        self.boxps.wait_feed_pass_done()

    def load_into_memory(self):
        """
        Load next pass into memory and notify boxps to fetch its emb from SSD
        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("BoxPSDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.load_into_memory()
	    """
        self._prepare_to_run()
        self.boxps.load_into_memory()

    def preload_into_memory(self):
        """
        Begin async preload next pass while current pass may be training
        Examples:
            .. code-block:: python

              import paddle.fluid as fluid
              dataset = fluid.DatasetFactory().create_dataset("BoxPSDataset")
              filelist = ["a.txt", "b.txt"]
              dataset.set_filelist(filelist)
              dataset.preload_into_memory()
        """
        self._prepare_to_run()
        self.boxps.preload_into_memory()

    def _dynamic_adjust_before_train(self, thread_num):
        if not self.is_user_set_queue_num:
            self.dataset.dynamic_adjust_channel_num(thread_num, True)
        self.dataset.dynamic_adjust_readers_num(thread_num)
